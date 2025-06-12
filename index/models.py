import uuid

from django.db import models


# Create your models here.

class Platform_Info(models.Model):
    id = models.AutoField(primary_key=True)
    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=True)
    platform_name = models.CharField(max_length=32, verbose_name="平台名称", unique=True)
    login_html = models.URLField(verbose_name="登录地址", null=True, blank=True)
    login_itf = models.CharField(max_length=128, verbose_name="登录接口")
    username = models.CharField(max_length=128, verbose_name="账号")
    password = models.CharField(max_length=512, verbose_name="密码")
    headers = models.CharField(max_length=256, verbose_name="请求头")
    auth_name = models.CharField(max_length=128, verbose_name="前端认证字段名", default="Authorization")
    auth_value = models.TextField(max_length=128, verbose_name="前端认证字段值", null=True, blank=True)
    token_name = models.CharField(max_length=128, verbose_name="后端返回的token字段名", null=True, blank=True)
    interval_time = models.IntegerField(default=1, verbose_name="通知间隔时间，单位(分钟)", null=True, blank=True)
    last_notice_time = models.CharField(max_length=64, verbose_name="上一次通知时间", null=True, blank=True)

    enabled = models.IntegerField(default=1, verbose_name="是否可用,0不可以，1可用")
    disabled_reason = models.TextField(verbose_name="不可用的原因", null=True, blank=True)
    max_retry_num = models.IntegerField(default=0, verbose_name="请求失败后，最大请求重试次数", null=True, blank=True)
    retry_num = models.IntegerField(default=0, verbose_name="请求失败次数", null=True, blank=True)
    is_notice = models.IntegerField(default=1, verbose_name="是否告警通知,0不是，1是")
    class Meta:
        db_table = "platform_info"


class InspectType(models.Model):
    id = models.AutoField(primary_key=True)
    inspectTypeName = models.CharField(max_length=32, verbose_name="巡检类型名称", unique=True)
    class Meta:
        db_table = "inspectType"

class Platform_Inspect_Item(models.Model):
    id = models.AutoField(primary_key=True)
    inspectTypeId = models.ForeignKey(to="InspectType", to_field="id", on_delete=models.CASCADE,
                                      related_name="inspectTypeId", null=True, blank=True, db_column="inspectTypeId")
    platform_inspect_item_name = models.CharField(max_length=32, verbose_name="平台巡检项名称", null=True, blank=True)
    webUrl = models.URLField(verbose_name="前端页面地址", null=True, blank=True)
    request_method = models.CharField(max_length=8, verbose_name="请求方法", null=True, blank=True)
    dataItf = models.CharField(max_length=128, verbose_name="数据接口", null=True, blank=True)
    platform_info_id = models.ForeignKey(to="Platform_Info", to_field="id", on_delete=models.CASCADE,
                                         related_name="platform_inspect_item", null=True, blank=True,
                                         db_column="platform_info_id")
    interval_time = models.IntegerField(default=1, verbose_name="通知间隔时间，单位(分钟)", null=True, blank=True)
    last_notice_time = models.CharField(max_length=64, verbose_name="上一次通知时间",null=True, blank=True)
    enabled = models.IntegerField(default=1, verbose_name="是否可用,0不可以，1可用,2告警")
    is_notice = models.IntegerField(default=1, verbose_name="是否告警时通知,0不通知，1通知")
    disabled_reason = models.TextField(verbose_name="不可用或告警的原因", null=True, blank=True)
    device_name = models.CharField(max_length=64, verbose_name="设备名称字段", null=True, blank=True)
    device_online_field = models.CharField(max_length=64, verbose_name="设备在线字段", null=True, blank=True)
    device_online_value = models.CharField(max_length=64, verbose_name="设备在线判定值", null=True, blank=True)
    ignore_devices = models.CharField(max_length=512, verbose_name="通知忽略设备(列表格式)", null=True, blank=True)
    notice_ignore_not_online_num = models.IntegerField(default=0, verbose_name="通知忽略设备后不在线设备个数", null=True, blank=True)
    last_not_online_device = models.CharField(max_length=1024, verbose_name="上一次巡检不在线的设备", null=True,
                                              blank=True)
    retry_num = models.IntegerField(default=0, verbose_name="请求失败次数", null=True, blank=True)

    class Meta:
        db_table = "platform_inspect_item"


class Inspect_Record(models.Model):
    id = models.AutoField(primary_key=True)
    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=True)
    platform_info_id = models.ForeignKey(to="Platform_Info", to_field="id", on_delete=models.CASCADE,
                                         related_name="platform_info", null=True, blank=True,
                                         db_column="platform_info_id")
    platform_inspect_id = models.ForeignKey(to="Platform_Inspect_Item", to_field="id", on_delete=models.CASCADE,
                                            related_name="platform_inspect_item", null=True, blank=True,
                                            db_column="platform_inspect_item_id")
    inspect_time = models.CharField(max_length=64, verbose_name="巡检时间")
    response_code = models.CharField(max_length=32, verbose_name="巡检响应码", null=True, blank=True)
    response_message = models.TextField(verbose_name="巡检结果", null=True, blank=True)

    class Meta:
        db_table = "inspect_record"
class Notice_Type(models.Model):
    id = models.AutoField(primary_key=True)
    notice_type_name = models.CharField(max_length=32, verbose_name="通知类型")
    class Meta:
        db_table = "notice_type"
class Notice_Config(models.Model):
    id = models.AutoField(primary_key=True)
    notice_type_id = models.ForeignKey(to="Notice_Type",to_field="id", on_delete=models.CASCADE,
                                            related_name="notice_type", null=True, blank=True,
                                            db_column="notice_type_id")
    notice_code = models.IntegerField(default=201, verbose_name="告警等级,和Inspect_Record的response_code值一致。200可用，201告警,500不可用")
    receiver_email = models.CharField(max_length=64, verbose_name="接收者邮箱", null=True, blank=True)
    webhook = models.CharField(max_length=128, verbose_name="企业微信webhook地址", null=True, blank=True)
    class Meta:
        db_table = "notice_config"

class Sys_User(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=32, verbose_name="用户名", null=True, blank=True, unique=True)
    account = models.CharField(max_length=32, verbose_name="账号", unique=True)
    password = models.CharField(max_length=128, verbose_name="密码")
    email = models.CharField(max_length=32, verbose_name="邮箱", null=True, blank=True)
    tel = models.CharField(max_length=32, verbose_name="电话号码", null=True, blank=True)

    class Meta:
        db_table = "sys_user"
#
# class Notice_Config(models.Model):
#     id = models.AutoField(primary_key=True)
#     sys_user_id = models.ForeignKey(to="Sys_User", to_field="id", on_delete=models.CASCADE, db_column="sys_user_id",
#                                     null=True, blank=True, related_name="sys_user")
#     notice_type = models.CharField(max_length=32, verbose_name="通知类型",null=True)
#     class Meta:
#         db_table = "notice_config"
#
# class Notice_Record(models.Model):
#     id = models.AutoField(primary_key=True)
#     sys_user_id = models.ForeignKey(to="Sys_User", to_field="id", on_delete=models.CASCADE,db_column="sys_user_id",null=True,blank=True,related_name="sys_user")
#     title = models.CharField(max_length=32, verbose_name="通知主题", null=True)
#     content = models.TextField(verbose_name="通知内容", null=True)
#     notice_time = models.CharField(max_length=32, verbose_name="通知时间", null=True)
#     class Meta:
#         db_table = "notice_record"
