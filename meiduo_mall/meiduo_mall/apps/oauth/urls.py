from django.conf.urls import urlfrom  . import viewsurlpatterns = [    # 返回qq扫描url    url(r'^qq/authorization/$', views.QQAuthURLView.as_view()),    # qq OAuth2.0 认证    url(r'^qq/user/$', views.QQAuthUserView.as_view()),]