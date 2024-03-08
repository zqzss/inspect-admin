import base64
import http
import json
import logging
import string
import traceback
from datetime import datetime,timedelta

from pyexpat import model
from cryptography.fernet import Fernet
import jwt

# 定时任务导入
from index.crond import auto_inspect

from django.forms import model_to_dict
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

# Create your views here.
from index.entity.Result import Result
from index.middleware import TokenAuthenticationMiddleware
from index.models import *
from django.core.paginator import Paginator

from django.contrib.auth.hashers import make_password, check_password

import logging

from inspect_admin import settings

logger = logging.getLogger(__name__)

@csrf_exempt
def login(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        account = data.get('username')
        password = data.get('password')
        try:
            user = model_to_dict(Sys_User.objects.filter(account=account).first())
        except Exception as e:
            result = Result(500, "", "账号或密码错误！")
            logger.info("用户: " + str(data) + "登录失败，账号或密码错误！")
            return JsonResponse(result.toDict())
        mpwd = user["password"]
        print("mpwd: ", mpwd)
        pwd_bool = check_password(password, mpwd)

        if pwd_bool:
            # 设置过期时间为当前时间 + 30 分钟
            expiry_time = datetime.utcnow() + timedelta(minutes=30)
            # 构建 payload
            payload = {
                'user_id': user["id"],
                'exp': expiry_time
            }
            token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
            result = Result(200, token, "登录成功")
            logger.info("用户: " + str(data) + "登录成功")
            return JsonResponse(result.toDict())
        else:
            result = Result(500, "", "账号或密码错误！")
            logger.info("用户: " + str(data) + "登录失败，账号或密码错误！")
            return JsonResponse(result.toDict())
    else:
        result = Result(500, "", "invalid request methods")

        return JsonResponse(result.toDict())

@csrf_exempt
def platform_info(request):
    if request.body:
        data = json.loads(request.body)
    else:
        data = {}
    print("data: ", data)
    id = data.get('id')
    platform_name = data.get('platformName') if data.get('platformName') != None else data.get('platform_name')
    username = data.get('username')
    password = data.get('password')
    login_html = data.get('login_html')
    login_itf = data.get('login_itf')
    headers = data.get('headers')
    headers = str(headers).replace("'", '"')
    auth_name = data.get('auth_name')
    auth_value = data.get('auth_value')
    token_name = data.get('token_name')
    interval_time = data.get('interval_time') if data.get('interval_time') != None else 30
    max_retry_num = data.get('max_retry_num') if data.get('max_retry_num') != None else 0
    result = None

    # 生成密钥
    key = "gGz-WVKI3Eo3fA-wJPQBbIg3zeKoi0pMYquuvpcgDZs=".encode('utf-8')

    # 创建加密解密器
    cipher_suite = Fernet(key)
    if request.method == 'POST':
        try:
            headers = json.loads(headers)

            # 加密明文
            plaintext = password.encode('utf-8')
            ciphertext = cipher_suite.encrypt(plaintext)
            password = ciphertext.decode('utf-8')

            if headers:
                keys_to_remove = [key for key in headers.keys() if key == ""]
                for key in keys_to_remove:
                    del headers[key]
            else:
                headers = None
            Platform_Info.objects.create(platform_name=platform_name, username=username, password=password,
                                         login_html=login_html, login_itf=login_itf, headers=headers,
                                         auth_name=auth_name, token_name=token_name, interval_time=interval_time,max_retry_num=max_retry_num)
            result = Result(200, "", "新添平台成功！")
        except Exception as e:
            logging.error(str(e))
            result = Result(500, "", "新添平台失败！" + str(e))
    elif request.method == 'DELETE':
        try:
            Platform_Info.objects.filter(id=id).delete()
            result = Result(200, "", "删除平台成功！")
        except Exception as e:
            logging.error(str(e))
            result = Result(500, "", "删除平台失败！" + str(e))
    elif request.method == 'PUT':
        try:
            # 判断密码是否被修改过，改过则加密明文存到数据库
            platform_info_one = Platform_Info.objects.filter(id=id).first()
            if password != platform_info_one.password:
                plaintext = password.encode('utf-8')
                ciphertext = cipher_suite.encrypt(plaintext).decode('utf-8')
                password = ciphertext

            headers = json.loads(headers)
            if headers:
                keys_to_remove = [key for key in headers.keys() if key == ""]
                for key in keys_to_remove:
                    del headers[key]
            else:
                headers = None

            Platform_Info.objects.filter(id=id).update(platform_name=platform_name, username=username,
                                                       password=password,login_html=login_html,
                                                       login_itf=login_itf, headers=headers, auth_name=auth_name,
                                                       auth_value=auth_value, interval_time=interval_time,token_name=token_name,max_retry_num=max_retry_num)

            result = Result(200, "", "修改平台成功！")
        except Exception as e:
            traceback.print_exc()
            logging.error(str(e))
            result = Result(500, "", "修改平台失败！" + str(e))

    elif request.method == 'GET':
        # 页面大小
        pageSize = request.GET.get('pageSize', 10)
        # 当前页码
        currentPage = request.GET.get('currentPage', 1)
        platform_name = request.GET.get("platformName")
        # currentPage = data.get('currentPage')
        # pageSize = data.get('pageSize')
        # print("currentPage: ", currentPage)
        # print("pageSize: ", pageSize)
        # print("platform_name", platform_name)
        if platform_name:
            platform_info_all = Platform_Info.objects.filter(platform_name__icontains=platform_name).order_by('id')
        else:
            platform_info_all = Platform_Info.objects.all().order_by('id')

        # 创建分页器
        paginator = Paginator(platform_info_all, pageSize)

        # 获取指定页码的 Page 对象
        try:
            # 如果paginator.page()查不到数据会报错
            page_obj = paginator.page(currentPage)

            page_list = [model_to_dict(instance) for instance in page_obj]

        except Exception as e:
            logging.error(str(e))
            page_list = []
        # 总共多少条数据
        total = paginator.count
        responseData = {}
        responseData['total'] = total
        responseData['page_list'] = page_list
        result = Result(200, responseData, "查询成功")
    else:
        result = Result(400, "", "invalid request methods")

    return JsonResponse(result.toDict())


@csrf_exempt
def platformInspectItem(request):
    if request.body:
        data = json.loads(request.body)
    else:
        data = {}
    id = data.get('id')
    platform_inspect_inspect_name = data.get('platform_inspect_inspect_name',"")
    inspectTypeName = data.get('inspectTypeName')
    web_url = data.get('webUrl')
    data_itf = data.get('dataItf')
    intervalTime = data.get('interval_time')
    if not intervalTime:
        intervalTime = 30
    platform_name = data.get('platformName')
    device_name = data.get('device_name')
    device_online_field = data.get('device_online_field')
    device_online_value = data.get('device_online_value')
    # 页面大小
    pageSize = data.get('pageSize', 10)
    # 当前页码
    currentPage = data.get('currentPage', 1)
    requestMethod = data.get('request_method')
    ignore_devices = data.get('ignore_devices')
    notice_ignore_not_online_num = data.get('notice_ignore_not_online_num') if data.get('notice_ignore_not_online_num') else 0

    requestMethodUpper = None
    if requestMethod != None:
        requestMethodUpper = requestMethod.upper()
    result = None

    inspectTypeEntity = InspectType.objects.filter(inspectTypeName=inspectTypeName).first()
    if request.method == 'POST':
        if inspectTypeName != "页面" and requestMethodUpper not in ["GET", "POST", "DELETE", "PUT"]:
            result = Result(500, "", "新添巡检项失败！请求方法不合法")
        else:
            try:
                # 通知忽略设备的数组格式转换列表类型
                if ignore_devices:
                    ignore_devices = ignore_devices.replace("[", "").replace("]", "").replace('"', "").replace("'", "").replace(" ", "").split(",")
                platform_info_one = Platform_Info.objects.filter(platform_name=platform_name).first()
                interval_time = int(intervalTime)

                if inspectTypeEntity.inspectTypeName == "页面":
                    data_itf = None
                    device_name = None
                    device_online_value = None
                    device_online_field = None
                elif inspectTypeEntity.inspectTypeName == "接口":
                    web_url = None
                    device_name = None
                    device_online_value = None
                    device_online_field = None
                elif inspectTypeEntity.inspectTypeName == "设备在线":
                    web_url = None
                Platform_Inspect_Item.objects.create(inspectTypeId=inspectTypeEntity, webUrl=web_url, dataItf=data_itf,
                                                     platform_info_id=platform_info_one, interval_time=intervalTime,
                                                     request_method=requestMethodUpper,
                                                     device_online_value=device_online_value,
                                                     device_online_field=device_online_field, device_name=device_name,ignore_devices=ignore_devices,notice_ignore_not_online_num=notice_ignore_not_online_num,
                                                     platform_inspect_inspect_name=platform_inspect_inspect_name)
                result = Result(200, "", "新添巡检项成功！")
            except Exception as e:
                traceback.print_exc()
                logging.error(str(e))
                result = Result(500, "", "新添巡检项失败！" + str(e))

    elif request.method == 'DELETE':
        try:
            Platform_Inspect_Item.objects.filter(id=id).delete()
            result = Result(200, "", "删除巡检项成功！")
        except Exception as e:
            logging.error(str(e))
            result = Result(500, "", "删除巡检项失败！" + str(e))
    elif request.method == 'PUT':
        print("notice_ignore_not_online_num: ", notice_ignore_not_online_num)
        if inspectTypeName != "页面" and requestMethodUpper not in ["GET", "POST", "DELETE", "PUT"]:
            result = Result(500, "", "修改巡检项失败！请求方法不合法")
        else:
            try:
                # 通知忽略设备的数组格式转换列表类型
                if ignore_devices:
                    ignore_devices = ignore_devices.replace("[", "").replace("]", "").replace('"', "").replace("'", "").replace(" ", "").split(",")
                if inspectTypeEntity.inspectTypeName == "页面":
                    data_itf = None
                    device_name = None
                    device_online_value = None
                    device_online_field = None
                elif inspectTypeEntity.inspectTypeName == "接口":
                    web_url = None
                    device_name = None
                    device_online_value = None
                    device_online_field = None
                elif inspectTypeEntity.inspectTypeName == "设备在线":
                    web_url = None
                platform_info_one = Platform_Info.objects.filter(platform_name=platform_name).first()
                Platform_Inspect_Item.objects.filter(id=id).update(inspectTypeId=inspectTypeEntity, webUrl=web_url,
                                                                   dataItf=data_itf, platform_info_id=platform_info_one,
                                                                   interval_time=intervalTime,
                                                                   request_method=requestMethodUpper,
                                                                   device_online_value=device_online_value,
                                                                   device_online_field=device_online_field,
                                                                   device_name=device_name,ignore_devices=ignore_devices,notice_ignore_not_online_num=notice_ignore_not_online_num
                                                                   ,platform_inspect_inspect_name=platform_inspect_inspect_name)
                result = Result(200, "", "修改巡检项成功！")
            except Exception as e:
                logging.error(str(e))
                result = Result(500, "", "修改平台失败！" + str(e))
    elif request.method == 'GET':
        # 页面大小
        pageSize = request.GET.get('pageSize', 10)
        # 当前页码
        currentPage = request.GET.get('currentPage', 1)
        platform_name = request.GET.get("platformName")

        if platform_name:
            platform_info_QureySet = Platform_Info.objects.filter(platform_name__icontains=platform_name)
            platform_info_list = [platform_info_one for platform_info_one in platform_info_QureySet]
            platform_inspect_item_all = Platform_Inspect_Item.objects.filter(platform_info_id__in=platform_info_list)
        else:
            platform_inspect_item_all = Platform_Inspect_Item.objects.all().order_by('id')

        # 创建分页器
        paginator = Paginator(platform_inspect_item_all, pageSize)

        # 获取指定页码的 Page 对象
        try:
            # 如果paginator.page()查不到数据会报错
            platform_inspect_item_page_objs = paginator.page(currentPage)
            page_list = []
            for obj in platform_inspect_item_page_objs:
                inspectTypeName = InspectType.objects.filter(id=obj.inspectTypeId.id).first().inspectTypeName
                platformName = Platform_Info.objects.filter(id=obj.platform_info_id.id).first().platform_name
                obj_dict = model_to_dict(obj)
                obj_dict['inspectTypeName'] = inspectTypeName
                obj_dict['platformName'] = platformName
                page_list.append(obj_dict)

        except Exception as e:
            traceback.print_exc()
            logging.error(e)
            page_list = []
        # 总共多少条数据
        total = paginator.count
        responseData = {}
        responseData['total'] = total
        responseData['page_list'] = page_list
        result = Result(200, responseData, "查询成功")
    else:
        result = Result(400, "", "invalid request methods")

    return JsonResponse(result.toDict())


def getPlatfromById(request):
    if request.method == "GET":
        id = request.GET.get('id')
        if id is not None:
            platformEntity = Platform_Info.objects.filter(id=id).first()
            if platformEntity is not None:
                responseData = model_to_dict(platformEntity)
            else:
                responseData = None
            result = Result(200, responseData, "查询成功")
        else:
            result = Result(400, "", "id not allowed null")
    else:
        result = Result(400, "", "invalid request methods")
    return JsonResponse(result.toDict())


def getPlatformInfoNamesAll(request):
    if request.method == "GET":
        platformInfoQuerySet = Platform_Info.objects.all()
        platformInfoNames = []
        for platformInfoEntity in platformInfoQuerySet:
            platformInfoNames.append(platformInfoEntity.platform_name)
        result = Result(200, platformInfoNames, "查询成功")
    else:
        result = Result(400, "", "invalid request methods")
    return JsonResponse(result.toDict())


def getPlatformInspectItemById(request):
    if request.method == "GET":
        platformInspectItemId = request.GET.get("id")
        platformInspectItemEntity = Platform_Inspect_Item.objects.filter(id=platformInspectItemId).first()
        if platformInspectItemEntity is not None:
            platformId = platformInspectItemEntity.platform_info_id.id
            platformInfoEntity = Platform_Info.objects.filter(id=platformId).first()
            platformName = platformInfoEntity.platform_name
            inspectTypeName = platformInspectItemEntity.inspectTypeId.inspectTypeName
            responseData = model_to_dict(platformInspectItemEntity)
            responseData["platformName"] = platformName
            responseData["inspectTypeName"] = inspectTypeName
        else:
            responseData = None
        result = Result(200, responseData, "查询成功！")
    else:
        result = Result(400, "", "invalid request methods")
    return JsonResponse(result.toDict())


def getInspectTypeNames(request):
    if request.method == "GET":
        inspectTypeNames = []
        inspectTypeQuerySet = InspectType.objects.all()
        for inspectType in inspectTypeQuerySet:
            inspectTypeNames.append(inspectType.inspectTypeName)
        result = Result(200, inspectTypeNames, "查询成功！")
    else:
        result = Result(400, "", "invalid request methods")
    return JsonResponse(result.toDict())


def getInspectResultByMulQuery(request):
    if request.method == "GET":
        params = request.GET
        # 请求所有的参数
        timeRangeStart = params.get("formData[timeRange][0]")
        print("timeRangeStart:", timeRangeStart)
        timeRangeEnd = params.get("formData[timeRange][1]")
        print("timeRangeEnd:", timeRangeEnd)
        dateRangeStart = params.get("formData[dateRange][0]")
        print("dateRangeStart:", dateRangeStart)
        dateRangeEnd = params.get("formData[dateRange][1]")
        print("dateRangeEnd:", dateRangeEnd)
        currentPage = params.get("currentPage")
        pageSize = params.get("pageSize")
        status = params.get("formData[status]", None)
        platformName = params.get("formData[platformName]")
        inspectTypeName = params.get("formData[inspectTypeName]")
        # 数据库查询巡检时间用到的变量
        startDateTime = ""
        endDateTime = ""
        # 获取当前时间
        current_time = datetime.now()
        # 格式化时间
        current_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
        # 提取日期部分
        if dateRangeStart is not None and dateRangeEnd is not None:
            dt_start_obj = datetime.strptime(dateRangeStart, '%Y-%m-%d %H:%M:%S')
            startDateTime = dt_start_obj.strftime('%Y-%m-%d')
            dt_end_obj = datetime.strptime(dateRangeEnd, '%Y-%m-%d %H:%M:%S')
            endDateTime = dt_end_obj.strftime('%Y-%m-%d')
        elif dateRangeStart is None and dateRangeEnd is None:
            # dt_start_obj = datetime.strptime(current_time, '%Y-%m-%d %H:%M:%S')
            # startDateTime = dt_start_obj.strftime('%Y-%m-%d')
            startDateTime = "1970-01-01 00:00:00"
            dt_end_obj = datetime.strptime(current_time, '%Y-%m-%d %H:%M:%S')
            endDateTime = dt_end_obj.strftime('%Y-%m-%d')
        else:
            result = Result(200, "", "不合法的日期范围")
            return JsonResponse(result.toDict())
        # 提取时间部分
        if timeRangeStart is not None and timeRangeEnd is not None:
            time_start_obj = datetime.strptime(timeRangeStart, '%Y-%m-%d %H:%M:%S')
            startDateTime = startDateTime + " " + time_start_obj.strftime('%H:%M:%S')
            time_end_obj = datetime.strptime(timeRangeEnd, '%Y-%m-%d %H:%M:%S')
            endDateTime = endDateTime + " " + time_end_obj.strftime('%H:%M:%S')
        elif timeRangeStart is None and timeRangeEnd is None:
            startDateTime = startDateTime + " " + '00:00:00'
            endDateTime = endDateTime + " " + "23:59:59"
        else:
            result = Result(200, "", "不合法的时间范围")
            return JsonResponse(result.toDict())
        # print("startDateTime:", startDateTime)
        # print("endDateTime:", endDateTime)
        # print("status: ", status)
        inspect_result_QuerySet =[]
        if platformName and status:
            platform_info_QuerySet = Platform_Info.objects.filter(platform_name__icontains=platformName)

            platform_info_list = [platform_info_one for platform_info_one in platform_info_QuerySet]

            if inspectTypeName:
                platform_inspect_item_QuerySet = Platform_Inspect_Item.objects.filter(inspectTypeId__inspectTypeName=inspectTypeName)
                inspect_result_QuerySet = Inspect_Record.objects.filter(platform_info_id__in=platform_info_list,
                                                                        response_code=status, inspect_time__range=(
                        startDateTime, endDateTime), platform_inspect_id__in=platform_inspect_item_QuerySet).order_by(
                    '-inspect_time')
            else:
                inspect_result_QuerySet = Inspect_Record.objects.filter(platform_info_id__in=platform_info_list,
                                                                    response_code=status, inspect_time__range=(
                startDateTime, endDateTime)).order_by('-inspect_time')
        elif platformName and not status:
            platform_info_QuerySet = Platform_Info.objects.filter(platform_name__icontains=platformName)

            platform_info_list = [platform_info_one for platform_info_one in platform_info_QuerySet]

            if inspectTypeName:
                platform_inspect_item_QuerySet = Platform_Inspect_Item.objects.filter(inspectTypeId__inspectTypeName=inspectTypeName)
                inspect_result_QuerySet = Inspect_Record.objects.filter(platform_info_id__in=platform_info_list,
                                                                        inspect_time__range=(
                                                                            startDateTime, endDateTime),
                                                                        platform_inspect_id__in=platform_inspect_item_QuerySet).order_by(
                    '-inspect_time')
            else:
                inspect_result_QuerySet = Inspect_Record.objects.filter(platform_info_id__in=platform_info_list,
                                                                    inspect_time__range=(
                                                                    startDateTime, endDateTime)).order_by(
                '-inspect_time')
        elif not platformName and status:
            if inspectTypeName:
                platform_inspect_item_QuerySet = Platform_Inspect_Item.objects.filter(inspectTypeId__inspectTypeName=inspectTypeName)
                inspect_result_QuerySet = Inspect_Record.objects.filter(response_code=status, inspect_time__range=(
                    startDateTime, endDateTime),platform_inspect_id__in=platform_inspect_item_QuerySet).order_by('-inspect_time')
            else:
                inspect_result_QuerySet = Inspect_Record.objects.filter(response_code=status, inspect_time__range=(
            startDateTime, endDateTime)).order_by('-inspect_time')
        elif not platformName and not status:

            if inspectTypeName:
                platform_inspect_item_QuerySet = Platform_Inspect_Item.objects.filter(inspectTypeId__inspectTypeName=inspectTypeName)
                platform_inspect_item_list = [platform_inspect_item for platform_inspect_item in platform_inspect_item_QuerySet]
                inspect_result_QuerySet = Inspect_Record.objects.filter(
                    inspect_time__range=(startDateTime, endDateTime),platform_inspect_id__in=platform_inspect_item_list).order_by('-inspect_time')
            else:
                inspect_result_QuerySet = Inspect_Record.objects.filter(
                inspect_time__range=(startDateTime, endDateTime)).order_by('-inspect_time')

        try:
            paginator = Paginator(inspect_result_QuerySet, pageSize)
            inspect_result_page_objs = paginator.page(currentPage)
            page_list = []

            for obj in inspect_result_page_objs:
                platformInfoEntity = Platform_Info.objects.filter(id=obj.platform_info_id.id).first()
                platformName = platformInfoEntity.platform_name
                # 后台端
                if obj.platform_inspect_id:
                    inspectTypeName = InspectType.objects.filter(
                        id=obj.platform_inspect_id.inspectTypeId.id).first().inspectTypeName
                    platformInspectItemEntity = Platform_Inspect_Item.objects.filter(
                        id=obj.platform_inspect_id.id).first()
                    webUrl = platformInspectItemEntity.webUrl
                    dataItf = platformInspectItemEntity.dataItf
                    obj_dict = model_to_dict(obj)
                    obj_dict['inspectTypeName'] = inspectTypeName
                    obj_dict['platformName'] = platformName
                    obj_dict['webUrl'] = webUrl
                    obj_dict['dataItf'] = dataItf
                # 登录端
                else:
                    inspectTypeName = "登录"
                    webUrl = platformInfoEntity.login_html
                    dataItf = platformInfoEntity.login_itf
                    obj_dict = model_to_dict(obj)
                    obj_dict['inspectTypeName'] = inspectTypeName
                    obj_dict['platformName'] = platformName
                    obj_dict['webUrl'] = webUrl
                    obj_dict['dataItf'] = dataItf
                page_list.append(obj_dict)
        except Exception as e:
            traceback.print_exc()
            logging.error(e)
            page_list = []
        # 总共多少条数据
        total = paginator.count
        responseData = {}
        responseData['total'] = total
        responseData['page_list'] = page_list
        result = Result(200, responseData, "查询成功")
    else:
        result = Result(400, "", "invalid request methods")
    return JsonResponse(result.toDict())


def getNoticeTypeNameAll(request):
    if request.method == "GET":
        noticeTypeQuerySet = Notice_Type.objects.all()
        noticeTypeNamesList = []
        for noticeType in noticeTypeQuerySet:
            noticeTypeNamesList.append(noticeType.notice_type_name)
        result = Result(200, noticeTypeNamesList, "查询成功")
    else:
        result = Result(400, "", "invalid request methods")
    return JsonResponse(result.toDict())


def noticeConfig(request):
    if request.body:
        data = json.loads(request.body)
    else:
        data = {}
    id = data.get('id')
    noticeTypeName = data.get('notice_type_name')
    webhook = data.get('webhook')
    receiverEmail = data.get('receiver_email')
    notice_code = data.get('notice_code')
    if request.method == "GET":
        noticeConfigQuerySet = Notice_Config.objects.all()
        noticeConfigList = []
        for noticeConfig in noticeConfigQuerySet:
            noticeConfigDict = model_to_dict(noticeConfig)
            noticeTypeName = Notice_Type.objects.filter(id=noticeConfig.notice_type_id.id).first().notice_type_name
            noticeConfigDict["notice_type_name"] = noticeTypeName
            noticeConfigList.append(noticeConfigDict)
        result = Result(200, noticeConfigList, "查询成功")
    elif request.method == "POST":
        try:
            noticeType = Notice_Type.objects.filter(notice_type_name=noticeTypeName).first()
            Notice_Config.objects.create(notice_type_id=noticeType, webhook=webhook, receiver_email=receiverEmail,notice_code=notice_code)
            result = Result(200, "", "新添通知配置成功")
        except Exception as e:
            traceback.print_exc()
            result = Result(500, "", "新添通知配置失败:" + str(e))
    elif request.method == "PUT":
        try:
            noticeType = Notice_Type.objects.filter(notice_type_name=noticeTypeName).first()
            if noticeType.notice_type_name == "邮箱":
                Notice_Config.objects.update(notice_type_id=noticeType, webhook=None, receiver_email=receiverEmail,notice_code=notice_code)
            elif noticeType.notice_type_name == "企业邮箱":
                Notice_Config.objects.update(notice_type_id=noticeType, webhook=webhook, receiver_email=None,notice_code=notice_code)
            result = Result(200, "", "修改通知配置成功")
        except Exception as e:
            traceback.print_exc()
            result = Result(500, "", "修改通知配置失败:" + str(e))
    elif request.method == "DELETE":
        try:
            Notice_Config.objects.filter(id=id).delete()
            result = Result(200, "", "删除通知配置成功")
        except Exception as e:
            traceback.print_exc()
            result = Result(500, "", "删除通知配置失败:" + str(e))
    else:
        result = Result(400, "", "invalid request methods")
    print(result.toDict())
    return JsonResponse(result.toDict())


def getNoticeConfigById(request):
    if request.method == "GET":
        try:
            id = request.GET.get("id")
            noticeConfigEntity = Notice_Config.objects.filter(id=id).first()
            noticeTypeName = Notice_Type.objects.filter(
                id=noticeConfigEntity.notice_type_id.id).first().notice_type_name
            noticeConfigDict = model_to_dict(noticeConfigEntity)
            noticeConfigDict["notice_type_name"] = noticeTypeName
            result = Result(200, noticeConfigDict, "查询成功")
        except Exception as e:
            traceback.print_exc()
            result = Result(500, "", "删除通知配置失败:" + str(e))
    else:
        result = Result(400, "", "invalid request methods")
    return JsonResponse(result.toDict())
