# 此文件作为celery启动入口
# 在入口文件主要做三件事: 1.创建celery客户端 Celery()  2.加载celery配置,(配置耗时任务存放的位置),
# 3.把耗时任务添加到任务队列
from celery import Celery

# 为celery使用django配置文件进行设置
import os
if not os.getenv('DJANGO_SETTINGS_MODULE'):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'meiduo_mall.settings.dev'


# 1.创建celery客户端  (里面的meiduo_sz20只是一个别名没有任何实际意思义,不写也行)
celery_app = Celery('meiduo_sz20')

# 2.加载配置
celery_app.config_from_object('celery_tasks.config')

# 3.注册任务
# celery_app.autodiscover_tasks('celery_tasks.sms')  任务将来可以有多个,一定要把任务放在列表中

celery_app.autodiscover_tasks(['celery_tasks.sms', 'celery_tasks.email', 'celery_tasks.html'])