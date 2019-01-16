# 编辑耗时任务
from .yuntongxun.sms import CCP
from . import constants
from celery_tasks.main import celery_app

# 用装饰器来装饰此函数为一个异步任务, 并指定任务的别名,别名没有什么实际意义,只因,默认的任务名称很长很长
@celery_app.task(name='send_sms_code')
def send_sms_code(mobile, sms_code):
    """发送短信"""
    CCP().send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES // 60], 1)