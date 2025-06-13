import logging
import os
import smtplib
import time, datetime

import traceback
from concurrent.futures import ThreadPoolExecutor
# from datetime import datetime,timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pytz
import urllib3

from apscheduler.schedulers.background import BackgroundScheduler

from index.models import *
from index.utils.methods import *

import requests
from requests.adapters import HTTPAdapter
import json
from django.forms import model_to_dict
from cryptography.fernet import Fernet
from inspect_admin.settings import inspect_interval_time, request_timeout, request_max_retries, while_max_time, \
    not_inspect_start_timeRange, not_inspect_end_timeRange, sender_email, sender_password

# 创建记录器
logger = logging.getLogger('simple')

logger_error = logging.getLogger('error')
# # 设置日志记录级别
# logger.setLevel(logging.INFO)
# # 创建处理器
# ch = logging.StreamHandler()
# # 设置处理器级别
# ch.setLevel(logging.INFO)
# # 创建格式器
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# # 为处理器设置格式器
# ch.setFormatter(formatter)
# # 将处理器添加到记录器
# logger.addHandler(ch)

# 禁止https证书警告输出
urllib3.disable_warnings()

# request请求超时时间
timeout = request_timeout

s = requests.Session()
s.mount('http://', HTTPAdapter(max_retries=request_max_retries))
s.mount('https://', HTTPAdapter(max_retries=request_max_retries))
# 禁用https证书校验过不过期
s.verify = False


def auto_inspect_platform_item(platform_info_inst):
    platform_info_one = model_to_dict(platform_info_inst)
    platform_inspect_item_querySet = Platform_Inspect_Item.objects.filter(platform_info_id=platform_info_inst)
    # 如果平台巡检次数不等于0，则不巡检平台巡检项
    if int(platform_info_inst.retry_num) != 0:
        return

    # 如果平台不可用，则修改所有与这平台有关的巡检项状态是不可用
    if int(platform_info_inst.enabled) == 0:
        for item in platform_inspect_item_querySet:
            Platform_Inspect_Item.objects.filter(id=item.id).update(enabled=0, disabled_reason="平台登录失败！",
                                                                    last_notice_time=None)
        return

    # 格式化时间
    now = datetime.datetime.now()
    # 设置时区为 UTC+8
    timezone = pytz.timezone('Asia/Shanghai')
    now = timezone.localize(now)
    # 将当前时间格式化为 "年-月-日 时:分:秒" 格式的字符串
    formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")

    # 定义记录巡检结果的变量
    # 巡检记录状态码
    response_code = 0
    # 巡检记录消息
    response_message = ""
    # enabled判断平台巡检项是否可用，1可用
    enabled = 1

    token_name = platform_info_one['token_name']

    for item in platform_inspect_item_querySet:
        headers = platform_info_one['headers']

        # 获取平台巡检项属性
        platform_inspect_item_dict = model_to_dict(item)
        inspect_type = item.inspectTypeId.inspectTypeName
        web_url = platform_inspect_item_dict['webUrl']
        auth_name = platform_info_one['auth_name']
        auth_value = platform_info_one['auth_value']
        data_itf = platform_inspect_item_dict['dataItf']
        requestMethod = platform_inspect_item_dict['request_method']
        device_name = platform_inspect_item_dict['device_name']
        device_online_field = platform_inspect_item_dict['device_online_field']
        device_online_value = platform_inspect_item_dict['device_online_value']
        is_notice = int(item.is_notice)

        # 忽略通知的设备名称列表
        ignore_devices = []
        if platform_inspect_item_dict['ignore_devices']:
            ignore_devices = platform_inspect_item_dict['ignore_devices'].replace("[", "").replace("]", "").replace('"',
                                                                                                                    "").replace(
                "'", "").replace(" ", "").split(",")
        # 上一次巡检不在线的设备名称
        last_not_online_device = []
        if platform_inspect_item_dict['last_not_online_device']:
            last_not_online_device = platform_inspect_item_dict['last_not_online_device'].replace("[", "").replace("]",
                                                                                                                   "").replace(
                '"', "").replace("'", "").replace(" ", "").split(",")
        # 接口返回的不在线的设备名称列表
        device_not_online_nameList = []

        # 用于网络请求的请求头字典
        try:
            headers_dict = json.loads(headers)
        except Exception as e:
            headers_dict = {}
        # 请求头添加token认证信息
        headers_dict[auth_name] = auth_value

        # 防止requests发生报错后res变量未定义
        res = None

        # 重试巡检次数
        retry_num = 0
        max_retry_num = -1

        # 巡检类型是页面
        if inspect_type == "页面":
            try:
                # res = s.get(web_url, headers=headers_dict,timeout=timeout)
                res = send_request_with_retry("get", web_url, headers=headers_dict)
                res.encoding = "utf-8"
                response_code = res.status_code
                if (0 <= response_code < 400):
                    response_message = "前端后台页面正常"
                    enabled = 1
                else:
                    enabled, response_code, response_message,retry_num = RequestNot200(res, platform_info_inst)

            except Exception as e:
                logger_error.error(e)
                logger_error.error(traceback.format_exc())
                traceback.print_exc()
                enabled, response_code, response_message, retry_num = RequestException(res, platform_info_inst, e)

            finally:
                # 关闭连接
                if res is not None:
                    res.close()
            logger.info(str(platform_info_one["platform_name"]) + " - 前端后台页面: " + web_url + " - 巡检结果: " + str(
                response_message))
        # 巡检类型是后端接口
        elif inspect_type == "接口":
            # 记录登录成功后接口返回的token值
            origin_auth_value = ""
            if auth_value:
                origin_auth_value = auth_value
            # 判断请求后端接口的token是否需要加前缀，如加"Bearer "。根据content-type内容决定发送表单数据还是json数据
            try:
                if "json" in headers:
                    # res = eval("s." + requestMethod.lower() + "(data_itf,headers=headers_dict,timeout=timeout)")
                    res = eval("send_request_with_retry('" + requestMethod.lower() + "',data_itf,headers=headers_dict)")
                else:
                    # res = eval("s." + requestMethod.lower() + "(data_itf, headers=headers_dict,timeout=timeout)")
                    res = eval(
                        "send_request_with_retry('" + requestMethod.lower() + "',data_itf,headers=headers_dict)")
                res_dict = json.loads(res.text)
                # 200或0表示成功，写死
                if 200 not in res_dict.values() and 0 not in res_dict.values():
                    auth_value = "Bearer " + origin_auth_value
            except Exception as e:
                auth_value = "Bearer " + origin_auth_value
            finally:
                # 关闭连接
                if res is not None:
                    res.close()

            # 更新请求头的token值
            headers_dict[auth_name] = auth_value

            try:
                if "json" in headers:
                    # res = eval("s." + requestMethod.lower() + "(data_itf,headers=headers_dict,timeout=timeout)")
                    res = eval("send_request_with_retry('" + requestMethod.lower() + "',data_itf,headers=headers_dict)")
                else:
                    res = eval("send_request_with_retry('" + requestMethod.lower() + "',data_itf,headers=headers_dict)")

                res.encoding = "utf-8"
                response_code = res.status_code
                if (0 <= response_code < 400):
                    response_message = "前端后台接口正常"
                    enabled = 1
                else:
                    enabled, response_code, response_message,retry_num = RequestNot200(res, platform_info_inst)
            except Exception as e:
                logger_error.error(e)
                logger_error.error(traceback.format_exc())
                traceback.print_exc()
                enabled, response_code, response_message, retry_num = RequestException(res, platform_info_inst, e)

            # 接口异常则不解析
            if response_code != 500:
                try:
                    # 后端接口返回的数据转换json报错说明接口不可用
                    res_dict = json.loads(res.text)
                    # 后端接口返回的数据转换json的值不包含200或0,则说明调用接口失败，巡检项不可用
                    if 200 in res_dict.values() or 0 in res_dict.values():
                        response_code = 200
                        response_message = "后端数据接口正常"
                        enabled = 1
                    else:
                        enabled, response_code, response_message,retry_num = RequestNot200(res, platform_info_inst)

                except Exception as e:
                    logger_error.error(e)
                    logger_error.error(traceback.format_exc())
                    traceback.print_exc()
                    enabled, response_code, response_message, retry_num = RequestException(res, platform_info_inst, e)

            # 关闭连接
            if res is not None:
                res.close()

            logger.info(str(platform_info_one["platform_name"]) + " - 后端数据接口" + data_itf + " - 巡检结果: " + str(
                response_message))

        elif inspect_type == "设备在线":
            # 记录登录成功后接口返回的token
            origin_auth_value = ""
            if auth_value:
                origin_auth_value = auth_value
            # 判断请求后端接口的token是否需要加前缀，如加"Bearer "。根据content-type内容决定发送表单数据还是json数据
            try:
                if "json" in headers:
                    # res = eval("s." + requestMethod.lower() + "(data_itf,headers=headers_dict,timeout=timeout)")
                    res = eval(
                        "send_request_with_retry('" + requestMethod.lower() + "',data_itf,headers=headers_dict)")
                else:
                    # res = eval("s." + requestMethod.lower() + "(data_itf, headers=headers_dict,timeout=timeout)")
                    res = eval(
                        "send_request_with_retry('" + requestMethod.lower() + "',data_itf,headers=headers_dict)")
                res_dict = json.loads(res.text)
                # 200或0表示成功，写死
                if 200 not in res_dict.values() and 0 not in res_dict.values():
                    auth_value = "Bearer " + origin_auth_value
            except Exception as e:
                auth_value = "Bearer " + origin_auth_value
            finally:
                # 关闭连接
                if res is not None:
                    res.close()
            # 更新请求头的token值
            headers_dict[auth_name] = auth_value

            # 把用户输入的设备在线字段路径转换为列表。如"/data/rows/status"转换成["data","rows","status"]
            device_online_field_list = [s for s in device_online_field.split("/") if s != '']

            try:

                if "json" in headers:
                    # res = eval("s." + requestMethod.lower() + "(data_itf,headers=headers_dict,timeout=timeout)")
                    res = eval("send_request_with_retry('" + requestMethod.lower() + "',data_itf,headers=headers_dict)")
                else:
                    res = eval("send_request_with_retry('" + requestMethod.lower() + "',data_itf,headers=headers_dict)")

                res.encoding = "utf-8"
                response_code = res.status_code
                if (0 <= response_code < 400):
                    response_message = "前端后台接口正常"
                    enabled = 1
                else:
                    enabled, response_code, response_message,retry_num = RequestNot200(res, platform_info_inst)

            except Exception as e:
                logger_error.error(e)
                logger_error.error(traceback.format_exc())
                traceback.print_exc()
                enabled, response_code, response_message, retry_num = RequestException(res, platform_info_inst, e)

            if response_code != 500:
                try:
                    # 后端接口返回的数据转换json报错说明接口不可用
                    res_dict = json.loads(res.text)
                    # 后端接口返回的数据转换json的值不包含200或0,则说明调用接口失败，巡检项不可用
                    if 200 in res_dict.values() or 0 in res_dict.values():
                        response_code = 200
                        # 设备在线信息列表
                        rows = []
                        # 接口返回的设备总个数
                        device_count = 0
                        # 接口返回的在线设备个数
                        device_online_count = 0
                        # 接口返回的不在线设备个数
                        device_not_online_count = 0
                        # 接口返回的不在线设备名称列表
                        device_not_online_nameList = []
                        # 根据设备在线字段路径找到接口返回的json数据里的设备信息列表
                        rows = res_dict
                        for i in range(len(device_online_field_list) - 1):
                            rows = rows[device_online_field_list[i]]
                        # 用户输入的设备在线字段路径的最后一个字段
                        last_device_online_field = device_online_field_list[-1]
                        for row in rows:
                            device_count += 1
                            if int(row[last_device_online_field]) != int(device_online_value):
                                device_not_online_count += 1
                                device_not_online_nameList.append(row[device_name])
                        if device_not_online_count > 0:
                            enabled = 2
                            # 201表示巡检记录的告警
                            response_code = 201
                            response_message = platform_info_inst.platform_name + " - 设备在线查询接口" + data_itf + " - 返回设备总个数: " + str(
                                device_count) + " - 不在线个数:" + str(
                                device_not_online_count) + " - 不在线设备名称: " + str(device_not_online_nameList)
                            # 更新平台巡检项的enable为2表示警告
                            Platform_Inspect_Item.objects.filter(id=item.id).update(enabled=enabled,
                                                                                    disabled_reason=response_message)
                        else:
                            response_code = 200
                            response_message = platform_info_inst.platform_name + " - 设备在线查询接口" + data_itf + " - 返回设备总个数: " + str(
                                device_count) + " - 不在线个数:" + str(
                                device_not_online_count) + " - 不在线设备名称: " + str(device_not_online_nameList)
                            enabled = 1
                        #  更新上次不在线设备名称列表
                        Platform_Inspect_Item.objects.filter(id=item.id).update(
                            last_not_online_device=device_not_online_nameList)
                    else:
                        enabled, response_code, response_message,retry_num = RequestNot200(res, platform_info_inst)

                except Exception as e:
                    logger_error.error(e)
                    logger_error.error(traceback.format_exc())
                    traceback.print_exc()
                    enabled, response_code, response_message, retry_num = RequestException(res, platform_info_inst, e)
            # 关闭连接
            if res is not None:
                res.close()

            logger.info(
                str(platform_info_one["platform_name"]) + " - 设备在线查询接口" + data_itf + " - 巡检结果: " + str(
                    response_message))
        Inspect_Record.objects.create(inspect_time=formatted_time, platform_info_id=platform_info_inst,
                                      platform_inspect_id=item,
                                      response_code=response_code, response_message=response_message)

        # 更新重试巡检次数
        Platform_Inspect_Item.objects.filter(id=item.id).update(retry_num=retry_num)

        # 如果还在重试巡检，则不发送消息通知
        if int(retry_num) > 0 and int(retry_num) <= int(max_retry_num):
            return

        # 如果平台巡检项状态是可用
        if enabled == 1:
            # 依据上一次通知时间是否为空判断是否发送过通知，如果发送过通知，依据通知等级发送恢复通知，并清空不可用的原因、更新状态和清空上一次通知的时间
            if item.last_notice_time:
                if item.inspectTypeId.inspectTypeName == "页面":
                    if not item.platform_inspect_item_name:
                        subject = platform_info_inst.platform_name + "页面访问失败"
                        message = formatted_time + "\n" + platform_info_inst.platform_name + " - " + item.webUrl + " - 页面访问失败" + " - 原因: " + item.disabled_reason
                    else:
                        subject = item.platform_inspect_item_name + "页面访问失败"
                        message = formatted_time + "\n" + item.platform_inspect_item_name + " - " + item.webUrl + " - 页面访问失败" + " - 原因: " + item.disabled_reason
                elif item.inspectTypeId.inspectTypeName == "接口":
                    if not item.platform_inspect_item_name:
                        subject = platform_info_inst.platform_name + "接口访问失败"
                        message = formatted_time + "\n" + platform_info_inst.platform_name + " - " + item.dataItf + " - 接口访问失败" + " - 原因: " + item.disabled_reason
                    else:
                        subject = item.platform_inspect_item_name + "接口访问失败"
                        message = formatted_time + "\n" + item.platform_inspect_item_name + " - " + item.dataItf + " - 接口访问失败" + " - 原因: " + item.disabled_reason
                elif item.inspectTypeId.inspectTypeName == "设备在线":
                    if not item.platform_inspect_item_name:
                        subject = platform_info_inst.platform_name + "设备在线告警"
                        message = formatted_time + "\n" + platform_info_inst.platform_name + " - " + item.dataItf + " - 设备在线告警" + " - 原因: " + item.disabled_reason
                    else:
                        subject = item.platform_inspect_item_name + "设备在线告警"
                        message = formatted_time + "\n" + item.platform_inspect_item_name + " - " + item.dataItf + " - 设备在线告警" + " - 原因: " + item.disabled_reason
                notice_Config_QuerySet = Notice_Config.objects.all()
                receiver_emails = []
                # 是否发送过通知
                isNoticeSuccess = 0
                # 设备的enabled转换巡检记录的response_code，设备的enabled对应response_code的字典
                notice_code_choice_dict = {0: 500, 1: 200, 2: 201}
                # 获取平台巡检项上一次发送通知的等级，即response_code
                enabled_code = notice_code_choice_dict[int(item.enabled)]

                for noticeConfigEntity in notice_Config_QuerySet:
                    # 判断告警时是否需要通知
                    if is_notice == 0:
                        break
                    # 获取通知配置的通知等级
                    notice_code = int(noticeConfigEntity.notice_code)

                    # 本次巡检是可用，如果平台巡检项上一次发送通知的等级大于通知配置的通知等级，则发恢复通知
                    # 发企业微信
                    if noticeConfigEntity.notice_type_id.notice_type_name == '企业微信' and enabled_code >= notice_code:
                        send_wechat_md(noticeConfigEntity.webhook, message, enabled)
                        isNoticeSuccess = 1
                    if noticeConfigEntity.notice_type_id.notice_type_name == '邮箱' and enabled_code >= notice_code:
                        receiver_emails.append(noticeConfigEntity.receiver_email)
                        isNoticeSuccess = 1
                # 发邮箱
                send_email(receiver_emails, subject, message)
                # # 更新上一次通知时间
                # if isNoticeSuccess == 1:
                #     Platform_Inspect_Item.objects.filter(id=item.id).update(last_notice_time=None)
            # 更新上一次通知时间和平台巡检项的状态和清空不可用的原因
            Platform_Inspect_Item.objects.filter(id=item.id).update(last_notice_time=None, enabled=enabled,
                                                                    disabled_reason=None)
        # 如果巡检项状态是不可用，则更新平台信息的状态为不可用、更新不可用的原因、更新上一次通知时间,根据间隔时间发通知
        elif enabled == 0:
            # 间隔时间
            interval_time = int(item.interval_time)
            last_notice_time = item.last_notice_time
            last_notice_datetime = datetime.datetime.strptime("2000-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")
            # 上一次的通知时间，如果不为空则表示不是第一次发送通知
            if last_notice_time:
                last_notice_datetime = datetime.datetime.strptime(last_notice_time, "%Y-%m-%d %H:%M:%S")
            current_datetime = datetime.datetime.now()
            # 计算两个时间之间的差异，并获取相差的分钟数
            minutes_diff = (current_datetime - last_notice_datetime).total_seconds() // 60
            # 当前时间和上次发送通知的间隔时间是否大于指定的间隔时间，大于则依据条件发通知。或者第一次发通知
            if minutes_diff >= interval_time or not item.last_notice_time:
                if item.inspectTypeId.inspectTypeName == "页面":
                    if not item.platform_inspect_item_name:
                        subject = platform_info_inst.platform_name + "页面访问失败"
                        message = formatted_time + "\n" + platform_info_inst.platform_name + " - " + item.webUrl + " - 页面访问失败" + " - 原因: " + str(
                            response_message)
                    else:
                        subject = item.platform_inspect_item_name + "页面访问失败"
                        message = formatted_time + "\n" + item.platform_inspect_item_name + " - " + item.webUrl + " - 页面访问失败" + " - 原因: " + str(
                            response_message)
                elif item.inspectTypeId.inspectTypeName == "接口":
                    if not item.platform_inspect_item_name:
                        subject = platform_info_inst.platform_name + "接口访问失败"
                        message = formatted_time + "\n" + platform_info_inst.platform_name + " - " + item.dataItf + " - 接口访问失败" + " - 原因: " + str(
                            response_message)
                    else:
                        subject = item.platform_inspect_item_name + "接口访问失败"
                        message = formatted_time + "\n" + item.platform_inspect_item_name + " - " + item.dataItf + " - 接口访问失败" + " - 原因: " + str(
                            response_message)
                elif item.inspectTypeId.inspectTypeName == "设备在线":
                    if not item.platform_inspect_item_name:
                        subject = platform_info_inst.platform_name + "设备在线告警"
                        message = formatted_time + "\n" + platform_info_inst.platform_name + " - " + item.dataItf + " - 设备在线告警" + " - 原因: " + str(
                            response_message)
                    else:
                        subject = item.platform_inspect_item_name + "设备在线告警"
                        message = formatted_time + "\n" + item.platform_inspect_item_name + " - " + item.dataItf + " - 设备在线告警" + " - 原因: " + str(
                            response_message)
                notice_Config_QuerySet = Notice_Config.objects.all()
                receiver_emails = []
                # 是否发送通知
                isNoticeSuccess = 0

                for noticeConfigEntity in notice_Config_QuerySet:
                    notice_code = int(noticeConfigEntity.notice_code)
                    # 判断告警时是否需要通知
                    if is_notice == 0:
                        break
                    # 本次巡检是可用，如果平台巡检项上一次发送通知的等级大于通知配置的通知等级，则发恢复通知
                    if noticeConfigEntity.notice_type_id.notice_type_name == '企业微信' and response_code >= notice_code:
                        send_wechat_md(noticeConfigEntity.webhook, message, enabled)
                        isNoticeSuccess = 1
                    if noticeConfigEntity.notice_type_id.notice_type_name == '邮箱' and response_code >= notice_code:
                        receiver_emails.append(noticeConfigEntity.receiver_email)
                        isNoticeSuccess = 1
                # 发邮箱
                send_email(receiver_emails, subject, message)

                # 更新上一次通知时间
                # if isNoticeSuccess == 1:
                # Platform_Inspect_Item.objects.filter(id=item.id).update(last_notice_time=formatted_time)
                Platform_Inspect_Item.objects.filter(id=item.id).update(last_notice_time=formatted_time)
            # 更新不可用的原因
            Platform_Inspect_Item.objects.filter(id=item.id).update(enabled=enabled,
                                                                    disabled_reason=response_message)
        # 如果巡检项状态是告警，需要判断上一次巡检是不是不可用，如果不是则更新平台信息的状态为告警、更新告警的原因、根据间隔时间和忽略设备和不在线个数发告警通知，否则发恢复通知
        elif enabled == 2:

            # 忽略设备
            ignore_devices_set = set(ignore_devices)
            # 用set集合得到不在线设备和忽略通知设备的差集
            device_not_online_nameSet = set(device_not_online_nameList)
            difference_ignore_devices_set = device_not_online_nameSet - ignore_devices_set
            difference_ignore_devices_list = list(difference_ignore_devices_set)

            # 配置的通知忽略设备后不在线设备个数
            notice_ignore_not_online_num = item.notice_ignore_not_online_num

            # 上一次巡检不在线设备的集合
            last_not_online_device_set = set(last_not_online_device)
            # 用set集合得到上一次通知设备和忽略设备的差集
            last_difference_not_online_devices_set = last_not_online_device_set - ignore_devices_set
            last_difference_not_online_devices_list = list(last_difference_not_online_devices_set)

            print("last_difference_not_online_devices_list", last_difference_not_online_devices_list)
            print("difference_ignore_devices_list", difference_ignore_devices_list)

            # 本次是告警，如果上一次巡检的状态是不可用，则发恢复通知
            if item.enabled == 0:
                if item.inspectTypeId.inspectTypeName == "页面":
                    if not item.platform_inspect_item_name:
                        subject = platform_info_inst.platform_name + "页面访问失败"
                        message = formatted_time + "\n" + platform_info_inst.platform_name + " - " + item.webUrl + " - 页面访问失败" + " - 原因: " + item.disabled_reason
                    else:
                        subject = item.platform_inspect_item_name + "页面访问失败"
                        message = formatted_time + "\n" + item.platform_inspect_item_name + " - " + item.webUrl + " - 页面访问失败" + " - 原因: " + item.disabled_reason
                elif item.inspectTypeId.inspectTypeName == "接口":
                    if not item.platform_inspect_item_name:
                        subject = platform_info_inst.platform_name + "接口访问失败"
                        message = formatted_time + "\n" + platform_info_inst.platform_name + " - " + item.dataItf + " - 接口访问失败" + " - 原因: " + item.disabled_reason
                    else:
                        subject = item.platform_inspect_item_name + "接口访问失败"
                        message = formatted_time + "\n" + item.platform_inspect_item_name + " - " + item.dataItf + " - 接口访问失败" + " - 原因: " + item.disabled_reason
                elif item.inspectTypeId.inspectTypeName == "设备在线":
                    if not item.platform_inspect_item_name:
                        subject = platform_info_inst.platform_name + "设备在线告警"
                        message = formatted_time + "\n" + platform_info_inst.platform_name + " - " + item.dataItf + " - 设备在线告警" + " - 原因: " + item.disabled_reason
                    else:
                        subject = item.platform_inspect_item_name + "设备在线告警"
                        message = formatted_time + "\n" + item.platform_inspect_item_name + " - " + item.dataItf + " - 设备在线告警" + " - 原因: " + item.disabled_reason
                notice_Config_QuerySet = Notice_Config.objects.all()
                receiver_emails = []
                # 是否发送过通知
                isNoticeSuccess = 0
                # 设备的enabled转换巡检记录的response_code，设备的enabled对应response_code的字典
                notice_code_choice_dict = {0: 500, 1: 200, 2: 201}
                # 获取平台巡检项上一次发送通知的等级，即response_code
                enabled_code = notice_code_choice_dict[int(item.enabled)]

                for noticeConfigEntity in notice_Config_QuerySet:
                    # 判断告警时是否需要通知
                    if is_notice == 0:
                        break
                    # 获取通知配置的通知等级
                    notice_code = int(noticeConfigEntity.notice_code)

                    # 本次是告警，如果上一次巡检的状态是不可用，则发恢复通知
                    # 发企业微信
                    if noticeConfigEntity.notice_type_id.notice_type_name == '企业微信':
                        send_wechat_md(noticeConfigEntity.webhook, message, 1)
                        isNoticeSuccess = 1
                    if noticeConfigEntity.notice_type_id.notice_type_name == '邮箱':
                        receiver_emails.append(noticeConfigEntity.receiver_email)
                        isNoticeSuccess = 1
                # 发邮箱
                send_email(receiver_emails, subject, message)
                # 更新上一次通知时间
                # if isNoticeSuccess == 1:
                #     Platform_Inspect_Item.objects.filter(id=item.id).update(enabled=enabled,last_notice_time=None)

                # 更新上一次通知时间和不可用的原因
                Platform_Inspect_Item.objects.filter(id=item.id).update(last_notice_time=None, enabled=enabled,
                                                                        disabled_reason=response_message)
            # 如果上一次巡检的状态是告警并且当前巡检状态也是告警，则根据忽略设备和通知忽略设备后不在线设备个数是否发恢复通知
            # 如果上次忽略设备后的差集存在，但本次巡检不存在而且依据告警等级发恢复通知
            elif (last_difference_not_online_devices_list and not difference_ignore_devices_list) or (
                    notice_ignore_not_online_num > 0 and len(
                    difference_ignore_devices_list) < notice_ignore_not_online_num) and item.last_notice_time:

                subject = platform_info_inst.platform_name + "设备在线告警"
                message = formatted_time + "\n" + platform_info_inst.platform_name + " - " + item.dataItf + " - 设备在线告警" + " - 原因: " + str(
                    item.disabled_reason)
                notice_Config_QuerySet = Notice_Config.objects.all()
                receiver_emails = []
                # 是否发送通知
                isNoticeSuccess = 0

                # 设备的enabled转换巡检记录的response_code，设备的enabled对应response_code的字典
                notice_code_choice_dict = {0: 500, 1: 200, 2: 201}
                # 获取平台巡检项上一次发送通知的等级，即response_code
                enabled_code = notice_code_choice_dict[int(item.enabled)]

                for noticeConfigEntity in notice_Config_QuerySet:
                    if is_notice == 0:
                        break
                    notice_code = int(noticeConfigEntity.notice_code)

                    # 发企业微信
                    if noticeConfigEntity.notice_type_id.notice_type_name == '企业微信' and enabled_code >= notice_code:
                        send_wechat_md(noticeConfigEntity.webhook, message, 1)
                        isNoticeSuccess = 1
                    if noticeConfigEntity.notice_type_id.notice_type_name == '邮箱' and enabled_code >= notice_code:
                        receiver_emails.append(noticeConfigEntity.receiver_email)
                        isNoticeSuccess = 1

                # 发邮箱
                send_email(receiver_emails, subject, message)

                # # 更新上一次通知时间
                # if isNoticeSuccess == 1:
                #     Platform_Inspect_Item.objects.filter(id=item.id).update(enabled=enabled, last_notice_time=None)

                # 更新上一次通知时间和告警的原因
                Platform_Inspect_Item.objects.filter(id=item.id).update(last_notice_time=None, enabled=enabled,
                                                                        disabled_reason=response_message)


            # 原来：如果当前巡检的状态是告警，则依据间隔时间和忽略设备发告警通知。因为difference_ignore_devices_list在ignore_devices为空时为空，所以不能使用elif difference_ignore_devices_list:
            # 现在：如果当前巡检的状态是告警，则依据间隔时间和忽略设备发告警通知。因为difference_ignore_devices_list在device_not_online_nameList为空时为空，所以不能使用elif difference_ignore_devices_list:
            else:
                # 间隔时间
                interval_time = int(item.interval_time)
                last_notice_time = item.last_notice_time
                last_notice_datetime = datetime.datetime.strptime("2000-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")
                # 上一次的通知时间，如果不为空则表示不是第一次发送通知
                if last_notice_time:
                    last_notice_datetime = datetime.datetime.strptime(last_notice_time, "%Y-%m-%d %H:%M:%S")
                current_datetime = datetime.datetime.now()
                # 计算两个时间之间的差异，并获取相差的分钟数
                minutes_diff = (current_datetime - last_notice_datetime).total_seconds() // 60

                # 当前时间和上次发送通知的间隔时间是否大于指定的间隔时间，大于并且忽略设备后不在线设备个数超过指定值则依据条件发告警通知
                if (minutes_diff >= interval_time and len(
                        difference_ignore_devices_list) >= notice_ignore_not_online_num) or (
                        not item.last_notice_time and len(
                        difference_ignore_devices_list) >= notice_ignore_not_online_num):
                    if item.inspectTypeId.inspectTypeName == "页面":
                        if not item.platform_inspect_item_name:
                            subject = platform_info_inst.platform_name + "页面访问失败"
                            message = formatted_time + "\n" + platform_info_inst.platform_name + " - " + item.webUrl + " - 页面访问失败" + " - 原因: " + str(
                                response_message)
                        else:
                            subject = item.platform_inspect_item_name + "页面访问失败"
                            message = formatted_time + "\n" + item.platform_inspect_item_name + " - " + item.webUrl + " - 页面访问失败" + " - 原因: " + str(
                                response_message)
                    elif item.inspectTypeId.inspectTypeName == "接口":
                        if not item.platform_inspect_item_name:
                            subject = platform_info_inst.platform_name + "接口访问失败"
                            message = formatted_time + "\n" + platform_info_inst.platform_name + " - " + item.dataItf + " - 接口访问失败" + " - 原因: " + str(
                                response_message)
                        else:
                            subject = item.platform_inspect_item_name + "接口访问失败"
                            message = formatted_time + "\n" + item.platform_inspect_item_name + " - " + item.dataItf + " - 接口访问失败" + " - 原因: " + str(
                                response_message)
                    elif item.inspectTypeId.inspectTypeName == "设备在线":
                        if not item.platform_inspect_item_name:
                            subject = platform_info_inst.platform_name + "设备在线告警"
                            message = formatted_time + "\n" + platform_info_inst.platform_name + " - " + item.dataItf + " - 设备在线告警" + " - 原因: " + str(
                                response_message)
                        else:
                            subject = item.platform_inspect_item_name + "设备在线告警"
                            message = formatted_time + "\n" + item.platform_inspect_item_name + " - " + item.dataItf + " - 设备在线告警" + " - 原因: " + str(
                                response_message)
                    notice_Config_QuerySet = Notice_Config.objects.all()
                    receiver_emails = []
                    # 是否发送通知
                    isNoticeSuccess = 0

                    for noticeConfigEntity in notice_Config_QuerySet:
                        if is_notice == 0:
                            break
                        notice_code = int(noticeConfigEntity.notice_code)
                        # 如果巡检类型是设备在线，需要多加一个条件不在线设备和忽略通知设备的差集不为空。接口和页面的巡检类型就不需要加多个条件判断
                        if item.inspectTypeId.inspectTypeName == "设备在线":
                            # 发企业微信
                            if noticeConfigEntity.notice_type_id.notice_type_name == '企业微信' and response_code >= notice_code and difference_ignore_devices_list:
                                send_wechat_md(noticeConfigEntity.webhook, message, enabled)
                                isNoticeSuccess = 1
                            if noticeConfigEntity.notice_type_id.notice_type_name == '邮箱' and response_code >= notice_code and difference_ignore_devices_list:
                                receiver_emails.append(noticeConfigEntity.receiver_email)
                                isNoticeSuccess = 1
                        else:
                            if noticeConfigEntity.notice_type_id.notice_type_name == '企业微信' and response_code >= notice_code:
                                send_wechat_md(noticeConfigEntity.webhook, message, enabled)
                                isNoticeSuccess = 1
                            if noticeConfigEntity.notice_type_id.notice_type_name == '邮箱' and response_code >= notice_code:
                                receiver_emails.append(noticeConfigEntity.receiver_email)
                                isNoticeSuccess = 1
                    # 发邮箱
                    send_email(receiver_emails, subject, message)

                    # 更新上一次通知时间
                    # if isNoticeSuccess == 1:
                    # Platform_Inspect_Item.objects.filter(id=item.id).update(last_notice_time=formatted_time)
                    Platform_Inspect_Item.objects.filter(id=item.id).update(last_notice_time=formatted_time)
                # 更新告警的原因
                Platform_Inspect_Item.objects.filter(id=item.id).update(enabled=enabled,
                                                                        disabled_reason=response_message)


# 巡检平台登录
def auto_inspect_platform_info(platform_info_inst):
    platform_info_one = model_to_dict(platform_info_inst)

    login_html = platform_info_one['login_html']
    # 数据库的header字段有'，需要转换"。如可能存在值{'':''}需要变成{}，不然请求报错
    try:
        platform_info_one['headers'] = platform_info_one['headers'].replace("'", "\"")
        headers = json.loads(platform_info_one['headers'])
    except Exception as e:
        logger_error.error(e)
        logger_error.error(traceback.format_exc())
        headers = {}
    headers_str = platform_info_one['headers']

    # 格式化时间
    # 获取当前时间
    now = datetime.datetime.now()
    # 设置时区为 UTC+8
    timezone = pytz.timezone('Asia/Shanghai')
    now = timezone.localize(now)
    # 将当前时间格式化为 "年-月-日 时:分:秒" 格式的字符串
    formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")

    # 定义记录巡检结果的变量
    # 巡检记录的状态码
    response_code = 0
    # 巡检记录消息
    response_message = ""
    # enabled判断平台信息是否可用
    enabled = 1
    # 防止requests发生报错后res变量未定义
    res = None
    # 重试巡检次数
    retry_num = 0
    max_retry_num = -1
    # 巡检html登录页面
    try:
        # res = s.get(login_html,headers=headers,timeout=timeout)
        res = send_request_with_retry("get", login_html, headers)
        res.encoding = "utf-8"
        response_code = res.status_code
        if (0 <= response_code < 400):
            response_message = "前端登录页面正常"
            enabled = 1
        else:
            enabled, response_code, response_message,retry_num = RequestNot200(res, platform_info_inst)

    except Exception as e:
        logger_error.error(e)
        logger_error.error(traceback.format_exc())
        traceback.print_exc()
        enabled, response_code, response_message,retry_num = RequestException(res, platform_info_inst, e)

    finally:
        # 关闭连接
        if res is not None:
            res.close()
    logger.info(str(platform_info_one["platform_name"]) + " - 前端登录页面: " + login_html + " - 巡检结果: " + str(
        response_message))

    # 如果登录页面巡检结果不可用并且是重试巡检，则不巡检登录接口
    if enabled == 1 and int(retry_num) == 0:
        # 获取平台属性
        auth_name = platform_info_one['auth_name']
        auth_value = None
        username = platform_info_one['username']
        login_itf = platform_info_one['login_itf']
        token_name = platform_info_one['token_name']

        # 解析平台登录密码
        # 生成密钥
        key = "gGz-WVKI3Eo3fA-wJPQBbIg3zeKoi0pMYquuvpcgDZs=".encode('utf-8')
        # 创建加密解密器
        cipher_suite = Fernet(key)
        # 解密密码
        password = platform_info_one['password']
        # 解密密文
        deciphertext = cipher_suite.decrypt(password.encode('utf-8'))
        password = deciphertext.decode("utf-8")

        # post请求登录接口的payload
        post_dict = {}
        post_dict['phone'] = username
        post_dict['username'] = username
        post_dict['userName'] = username
        post_dict['password'] = password
        post_dict['pwd'] = password
        post_dict['tenantId'] = None
        # 智慧工地接口需要携带的字段
        post_dict['grant_type'] = "password"
        post_dict['grantType'] = "password"
        post_dict['terminal'] = 1
        # 演示-智慧管廊需要携带的字段字段
        post_dict['captcha'] = ""
        # platform_info_inst = Platform_Info.objects.filter(id=platform_info_inst.id).first()[0]

        # 根据content-type内容发送表单数据还是json数据
        try:
            if "json" in headers_str:
                # res = s.post(login_itf, headers=headers, data=json.dumps(post_dict),timeout=timeout)
                res = send_request_with_retry("post", login_itf, headers=headers, data=json.dumps(post_dict))
            else:
                # res = s.post(login_itf, headers=headers, data=json.dumps(post_dict),timeout=timeout)
                res = send_request_with_retry("post", login_itf, headers=headers, data=post_dict)

            res.encoding = "utf-8"
            response_code = res.status_code
            if (0 <= response_code < 400):
                response_message = "后端登录接口正常"
                enabled = 1
            else:
                enabled,response_code,response_message,retry_num = RequestNot200(res,platform_info_inst)

        except Exception as e:
            logger_error.error(e)
            logger_error.error(traceback.format_exc())
            traceback.print_exc()
            enabled,response_code,response_message,retry_num = RequestException(res,platform_info_inst,e)

        # 判断是否登录成功,登录成功则json解析，登录后找到token值，找不到token值判断登录失败
        res_dict = ""
        if response_code != 500:
            try:
                res_dict = json.loads(res.text)
                # 把token路径字符串变成列表，"/data/token"变成 ['data','token']
                if "/" in token_name:
                    # 如果变量中包含分隔符 "/", 则将其按照 "/" 分隔成一个列表
                    token_name_list = [i for i in token_name.split("/") if i]
                else:
                    # 否则，直接将变量转换成一个列表
                    token_name_list = [token_name]
                # 根据token路径列表找到token字段所属的对象
                rows = res_dict
                for i in range(len(token_name_list) - 1):
                    rows = rows[token_name_list[i]]
                # 判断用户输入的token路径和接口返回的是否一致
                if token_name_list[-1] in rows:
                    auth_value = rows[token_name_list[-1]]
                    response_code = 200
                    response_message = "后端登录接口正常"
                    enabled = 1
                else:
                    auth_value = None
                    response_code = 500
                    response_message = "账号密码错误，或token路径不正确 "
                    if res != None and res.text != None:
                        response_message = response_message + res.text
                    # 不可用状态的最大巡检次数
                    retry_num = platform_info_inst.retry_num + 1
                    max_retry_num = platform_info_inst.max_retry_num
                    if retry_num > max_retry_num:
                        enabled = 0

                    else:
                        enabled = 1

                Platform_Info.objects.filter(id=platform_info_one["id"]).update(auth_value=auth_value)

            except Exception as e:
                logger_error.error(e)
                logger_error.error(traceback.format_exc())
                traceback.print_exc()
                enabled, response_code, response_message,retry_num = RequestException(res, platform_info_inst, e)

        # 关闭连接
        if res is not None:
            res.close()

        logger.info(str(platform_info_one["platform_name"]) + " - 后端登录接口: " + login_itf + " - 巡检结果: " + str(
            response_message))

    # 记录巡检记录
    Inspect_Record.objects.create(inspect_time=formatted_time, platform_info_id=platform_info_inst,
                                  response_code=response_code, response_message=response_message)

    # 更新重试巡检次数
    Platform_Info.objects.filter(id=platform_info_inst.id).update(retry_num=retry_num)

    # 如果还在重试巡检，则不发送消息通知
    if int(retry_num) > 0 and (int(retry_num) <= int(max_retry_num)):
        return

    # 判断是否告警不通知
    if platform_info_one["is_notice"] == 0:
        return

    # 如果登录成功，则更新平台信息的状态可用,依据上一次的状态发通知
    if enabled == 1:
        # 依据不可用的原因是否为空判断是否发送过通知，如果发送过通知，则发送恢复通知，并清空不可用的原因、更新状态和清空上一次通知的时间
        if platform_info_inst.disabled_reason and platform_info_inst.disabled_reason != "":
            subject = platform_info_inst.platform_name + "登录失败"
            message = formatted_time + "\n" + platform_info_inst.platform_name + " - " + "登录失败" + " - 原因: " + str(
                platform_info_one["disabled_reason"])
            notice_Config_QuerySet = Notice_Config.objects.all()
            receiver_emails = []
            isNoticeSuccess = 0
            for noticeConfigEntity in notice_Config_QuerySet:
                # 发企业微信
                if noticeConfigEntity.notice_type_id.notice_type_name == '企业微信':
                    send_wechat_md(noticeConfigEntity.webhook, message, enabled)
                    isNoticeSuccess = 1
                if noticeConfigEntity.notice_type_id.notice_type_name == '邮箱':
                    receiver_emails.append(noticeConfigEntity.receiver_email)
                    isNoticeSuccess = 1
            # 发邮箱
            send_email(receiver_emails, subject, message)

            # 更新上一次通知时间
            # if isNoticeSuccess == 1:
            #     Platform_Info.objects.filter(id=platform_info_one["id"]).update(last_notice_time=None)
            Platform_Info.objects.filter(id=platform_info_one["id"]).update(last_notice_time=None)
        # 更新不可用的原因为空
        Platform_Info.objects.filter(id=platform_info_one["id"]).update(enabled=enabled, disabled_reason=None)

    # 如果登录失败，则更新平台信息的状态为不可用、不可用的原因、更新上一次通知时间,根据间隔时间发告警通知
    elif enabled == 0:
        interval_time = int(platform_info_inst.interval_time)
        last_notice_time = platform_info_inst.last_notice_time
        last_notice_datetime = datetime.datetime.strptime("2000-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")
        if last_notice_time:
            last_notice_datetime = datetime.datetime.strptime(last_notice_time, "%Y-%m-%d %H:%M:%S")
        current_datetime = datetime.datetime.now()
        # 计算两个时间之间的差异，并获取相差的分钟数
        minutes_diff = int((current_datetime - last_notice_datetime).total_seconds() // 60)

        if minutes_diff >= interval_time or not platform_info_inst.last_notice_time:
            subject = platform_info_one["platform_name"] + " - 登录失败"
            message = formatted_time + "\n" + platform_info_one["platform_name"] + " - 登录失败" + " - 原因: " + str(
                response_message)
            notice_Config_QuerySet = Notice_Config.objects.all()
            receiver_emails = []
            isNoticeSuccess = 0
            for noticeConfigEntity in notice_Config_QuerySet:
                # 发企业微信
                if noticeConfigEntity.notice_type_id.notice_type_name == '企业微信':
                    send_wechat_md(noticeConfigEntity.webhook, message, enabled)
                    isNoticeSuccess = 1
                if noticeConfigEntity.notice_type_id.notice_type_name == '邮箱':
                    receiver_emails.append(noticeConfigEntity.receiver_email)
                    isNoticeSuccess = 1
            # 发邮箱
            send_email(receiver_emails, subject, message)

            # 更新上一次通知时间
            # if isNoticeSuccess == 1:
            # Platform_Info.objects.filter(id=platform_info_inst.id).update(last_notice_time=formatted_time)
            Platform_Info.objects.filter(id=platform_info_inst.id).update(last_notice_time=formatted_time)
        # 更新不可用的原因
        Platform_Info.objects.filter(id=platform_info_one["id"]).update(enabled=enabled,
                                                                        disabled_reason=response_message)


def send_email(receiver_emails, subject, message):
    server = smtplib.SMTP_SSL('smtp.exmail.qq.com', 465)
    server.login(sender_email, sender_password)
    for receiver_email in receiver_emails:
        msg = MIMEMultipart('mixed')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = receiver_email
        # html = """
        #             <h1>Hello world</h1>
        #         """
        msg.attach(MIMEText(message, ))
        server.sendmail(sender_email, receiver_email, msg.as_string())


# 发送markdown消息
def send_wechat_md(webhook, content, enable):
    header = {
        "Content-Type": "application/json",
        "Charset": "UTF-8"
    }
    if enable == 1:
        data = {
            "msgtype": "markdown",
            "markdown": {
                "content": "<font color=\"info\">[已恢复]</font>\n" + content
            }
        }
    else:
        data = {

            "msgtype": "markdown",
            "markdown": {
                "content": "<font color=\"warning\">[告警]</font>\n" + content
            }
        }
    payload = json.dumps(data)
    res = s.post(url=webhook, data=payload, headers=header, timeout=timeout)
    logger.info("企业微信发送消息: " + content)
    logger.info("企业微信告警返回结果: " + res.text)
    res_data = json.loads(res.text)
    if res_data["errcode"] and res_data["errcode"] != 0:
        payload = json.dumps({"msgtype": "markdown", "markdown": {"content" : "告警重发\n" + data["markdown"]["content"][:2000]}})
        res = s.post(url=webhook, data=payload, headers=header, timeout=timeout)
        logger_error.error("告警重发\n" + "企业微信发送消息: " + payload)
        logger_error.error("告警重发\n" + "企业微信告警返回结果: " + res.text)
    res.close()


def send_request_with_retry(method, url, headers, data=None):
    timeout = request_timeout  # 请求超时时间（秒）
    while_timeout = while_max_time  # 死循环总等待时间（秒）
    start_time = time.time()
    message = None
    if method == "get":
        while True:
            try:
                response = s.get(url, headers=headers, timeout=timeout, verify=False, allow_redirects=True)
                # if 0 <= response.status_code < 500:
                return response
            except Exception as e:
                message = str(e)
                # logger_error.error(e)
                # logger_error.error(traceback.format_exc())
            # 间隔时间，单位为s
            elapsed_time = time.time() - start_time
            if elapsed_time >= while_timeout:
                if message == None:
                    message = response.text
                break
            time.sleep(1)
    elif method == "post":
        while True:
            try:
                response = s.post(url, headers=headers, data=data, timeout=timeout, verify=False)
                # if 0 <= response.status_code < 500:
                return response
            except Exception as e:
                # message = traceback.format_exc()
                message = str(e)
                # logger_error.error(e)
                # logger_error.error(traceback.format_exc())
            # 间隔时间，单位为s
            elapsed_time = time.time() - start_time
            if elapsed_time >= while_timeout:
                if message == None:
                    message = response.text
                break
            time.sleep(0.3)
    # print("response.status_code: ",response.status_code)
    raise ConnectionError(message)


def mid_task(platform_info_inst):
    if not_inspect_start_timeRange and not_inspect_end_timeRange:
        # 判断是否在不巡检的时间段
        not_inspect_start_timeRange_hour = int(not_inspect_start_timeRange.split(":")[0])
        not_inspect_start_timeRange_minute = int(not_inspect_start_timeRange.split(":")[1])
        not_inspect_end_timeRange_hour = int(not_inspect_end_timeRange.split(":")[0])
        not_inspect_end_timeRange_minute = int(not_inspect_end_timeRange.split(":")[1])
        # 获取当前时间
        now = datetime.datetime.now()
        # 获取当前时间
        current_time = now.time()
        # 设置起始时间和结束时间
        start_time = datetime.time(not_inspect_start_timeRange_hour, not_inspect_start_timeRange_minute)  # 09:00
        end_time = datetime.time(not_inspect_end_timeRange_hour, not_inspect_end_timeRange_minute)  # 09:30
        if start_time <= current_time <= end_time:
            return

    # 开始巡检
    try:
        auto_inspect_platform_info(platform_info_inst)
        auto_inspect_platform_item(platform_info_inst)
    except Exception as e:
        logger_error.error(e)
        logger_error.error(traceback.format_exc())
        traceback.print_exc()


def auto_delete_inspect_record():
    now = datetime.datetime.now()
    seven_days_ago = now - datetime.timedelta(days=10)
    seven_days_ago_str = seven_days_ago.strftime('%Y-%m-%d %H:%M:%S')
    logger.info("seven_days_ago_str: %s", seven_days_ago_str)

    Inspect_Record.objects.extra(where=["inspect_time < %s"], params=[seven_days_ago_str]).delete()
    logger.info("删除10天前的巡检记录成功！")


try:
    def my_task():
        platform_info_all_querySet = Platform_Info.objects.all()
        # 定时任务先巡检平台登录
        max_threads = int(os.cpu_count() * 3 / 4)
        executor = ThreadPoolExecutor(max_workers=max_threads)
        threads = []
        for platform_info_inst in platform_info_all_querySet:
            # inspectPlatformInfoThread = threading.Thread(target=auto_inspect_platform_info,args=(platform_info_inst,),)
            # inspectPlatformInfoThread.start()
            executor.submit(mid_task, platform_info_inst)
            # threads.append(inspectPlatformInfoThread)

        # for thread in threads:
        #     thread.join()
        executor.shutdown()
        logger.info("定时任务执行成功！")


    max_instances = int(os.cpu_count() * 3 / 4)
    # 创建调度器
    scheduler = BackgroundScheduler()

    # 添加定时任务，定时巡检平台
    scheduler.add_job(my_task, 'interval', seconds=inspect_interval_time, max_instances=max_instances)
    # 添加定时任务，定时删除巡检记录
    scheduler.add_job(auto_delete_inspect_record, 'cron', hour='1', minute='0', second='0', max_instances=max_instances)
    # 启动调度器
    scheduler.start()
except Exception as e:
    logger_error.error(e)
    logger_error.error(traceback.format_exc())
    traceback.print_exc()
    send_wechat_md("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=55bc5c96-c883-42bf-8fef-df02fc9d3419",
                   "警告：定时任务崩溃！")
