xd: 先理解数据库字段意思、业务和逻辑，不然很容易出bug

1、定时任务插件安装了django_apscheduler和apscheduler，使用的是apscheduler

2、项目依赖的包
pip3 install django==4.2.2
pip3 install cryptography==3.4.7
pip3 install django django_apscheduler pymysql requests django-cors-headers pyJWT urllib3==1.26.15 apscheduler

3、linux服务器监听的端口
python3 manage.py runserver 0.0.0.0:7000

4、同步数据库表结构
python manage.py makemigrations
python manage.py migrate

5、 数据库表初始化。
insert into inspectType values("接口");
insert into inspectType values("页面");
insert into inspectType values("设备在线");

insert into notice_type values("邮箱");
insert into notice_type values("企业微信")

6、平台密码加密使用对称可逆库cryptography，参考：https://blog.51cto.com/u_16175470/7211853
# 加密密钥
key = "gGz-WVKI3Eo3fA-wJPQBbIg3zeKoi0pMYquuvpcgDZs=".encode('utf-8')

7、用户登录成功后用jwt库生成token
# jwt签名token的秘钥
JWT_SECRET = 'abc123'
# jwt签名算法
JWT_ALGORITHM = 'HS256'

8、用户密码使用from django.contrib.auth.hashers import make_password, check_password 加密和校验。需在settings.py配置加密校验器
Django提供了多种加密解密密码的方式：
项目使用方式1

①使用内置的make_password函数加密密码，使用check_password函数验证密码：
from django.contrib.auth.hashers import make_password, check_password
# 加密密码
password = make_password('my_password')
# 验证密码
is_correct = check_password('my_password', password)

②使用PBKDF2算法加密密码，这是Django默认的密码加密方式：
from django.utils.crypto import pbkdf2, constant_time_compare
# 加密密码
iterations = 36000
salt = 'random_salt'
password = 'my_password'
hash = pbkdf2(password, salt, iterations)
# 验证密码
is_correct = constant_time_compare(hash, pbkdf2(password, salt, iterations))

③自定义密码加密方式，可以通过在settings.py文件中设置PASSWORD_HASHERS来指定密码加密方式。例如，可以使用bcrypt算法：
python
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

9、日志打印时间少8小时，需在settings.py设置TIME_ZONE = 'Asia/Shanghai'

10、使用traceback模块可以在try-except语句里详细获取追踪报错的信息

11、项目日志使用django结合logging，logger记录器用于确认日志等级，handler处理器用于决定把日志输出到终端还是文件，formatters格式器用于格式打印日志。参考：https://blog.csdn.net/zhouxuan612/article/details/114832470  https://www.jb51.net/article/282448.htm

12、retry_num和max_retry_num只用于网络请求失败，平台巡检项的max_retry_num来自平台信息的max_retry_num


注意事项：
    被坑了，浏览器发生跨域和axios请求响应拦截器和后端都有关。stoken中间件配置和setting跨域配置
    发恢复通知后last_notice_time等于空

部署步骤（参考：https://blog.csdn.net/weixin_52107400/article/details/129065320):
    1、安装virtualenv
        pip3 install virtualenv
    2、建立软链接。在根目录建立文件夹/data/virtualenv/，主要用于存放env
        ln -s /usr/local/python3/bin/virtualenv /usr/bin/virtualenv
        mkdir -p /data/virtualenv/
    3、进入/data/virtualenv/下，创建虚拟环境
        virtualenv --python=/usr/bin/python3 环境名字
    4、启动虚拟环境
        cd /data/virtualenv/环境名字
        source activate
    5、退出虚拟环境
        deactivate
