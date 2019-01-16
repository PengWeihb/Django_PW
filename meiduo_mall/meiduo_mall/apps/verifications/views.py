from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
import random
import logging
from django_redis import get_redis_connection
from rest_framework import status

from . import constants
from meiduo_mall.libs.yuntongxun.sms import CCP
from celery_tasks.sms.tasks import send_sms_code

logger = logging.getLogger('django')  # 获取日志输入出器

# Create your views here.
class SMSCodeView(APIView):
    """发送短信视图"""

    def get(self, request, mobile):
        """
        GET /sms_codes/(?P<mobile>1[3-9]\d{9})/
        :param request: Request类型的请求对象
        :param mobile:  手机号
        :return: Response
        """
        # 连接redis
        redis_conn = get_redis_connection('verify_codes')
        # 获取send_flag
        send_flag = redis_conn.get('send_flag_%s' % mobile)

        # 判断send_flag有没有值,没有说明不是重复发送
        if send_flag:
            return Response({'message': '频繁发送短信'}, status=status.HTTP_400_BAD_REQUEST)

        # 生成短信验证码
        sms_code = '%06d' % random.randint(0, 999999)
        logger.info(sms_code)

        # 创建管道  好处:减少redis访问次数,提升性能
        pl = redis_conn.pipeline()

        # 把短信验证码缓存到redis  setex(key 过期时间, value)
        # redis_conn.setex('sms_%s' % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        pl.setex('sms_%s' % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)

        # 在redis中存储一个标识,用来标记此号码已经在60s内发送过短信
        # redis_conn.setex('send_flag_%s' % mobile, constants.SEND_FLAG_TIME_INTERVAL, 1)
        pl.setex('send_flag_%s' % mobile, constants.SEND_FLAG_TIME_INTERVAL, 1)

        # 让管道去执行,让里面的redis命令
        pl.execute()
        # 使用容联云通讯去发送短信  send_template_sms(self, to, datas, temp_id)
        # 下面的代码是一个耗时的操作,它会阻塞响应
        # CCP().send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES // 60], 1)

        # 任务函数.delay(任务函数的相应参数)
        send_sms_code.delay(mobile, sms_code)

        # 响应结果
        return Response({'message': 'ok'})
