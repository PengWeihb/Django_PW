from alipay import AliPay
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import os

from orders.models import OrderInfo
from .models import Payment

# Create your views here.

class PaymentStatusView(APIView):
    """修改订单的状态及保存支付信息(支付宝流水号和订单编号)"""
    # 设置权限,只有登录用户才能访问
    # permission_classes = [IsAuthenticated]

    def put(self, request):

        # 1.提取前端传入的查询参数
        query_dict = request.query_params
        # 把query_dict类型转换成Python标准字典
        data = query_dict.dict()

        # 提取url中的签名部分
        signature = data.pop('sign')

        # 2.创建支付宝支付对象
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys/app_private_key.pem"),
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "keys/alipay_public_key.pem"),  # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=settings.ALIPAY_DEBUG  # 默认False
        )

        # 验证支付状态,是否正常
        success = alipay.verify(data, signature)
        # 如果验证没有问题,就执行相应的保存和修改
        if success:

            # 取出订单编号
            order_id = data.get('out_trade_no')
            # 取出支付流水号
            trade_id = data.get('trade_no')
            # 保存支付信息到Payment模型/表(订单号和交易流水号)
            Payment.objects.create(
                order_id=order_id,
                trade_id=trade_id
            )

            # 修改订单状态由待支付更新为待发货
            OrderInfo.objects.filter(order_id=order_id, status=OrderInfo.ORDER_STATUS_ENUM['UNPAID']).update(status=OrderInfo.ORDER_STATUS_ENUM['UNSEND'])


            # 响应支付宝订单流水号  trade_id
            return Response({'trade_id': trade_id})
        else:
            return Response({'message': '非法请求'}, status=status.HTTP_403_FORBIDDEN)




class PaymentView(APIView):
    """获取支付宝的登录链接"""

    # 设置权限,只有登录用户才能访问
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        """返回支付宝登录链接"""

        # 获取当前要去支付的用户
        user = request.user
        try:
            # 校验订单id的真实性
            order = OrderInfo.objects.get(order_id=order_id, user=user, status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'])
        except OrderInfo.DoesNotExist:
            return Response({'message': '订单有误'}, status=status.HTTP_400_BAD_REQUEST)

        # 创建支付宝支付对象
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys/app_private_key.pem"),
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "keys/alipay_public_key.pem"),  # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=settings.ALIPAY_DEBUG  # 默认False
        )

        # 创建支付的url后面的请求参数
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(order.total_amount),
            subject="美多商城%s" % order_id,
            return_url="http://www.meiduo.site:8080/pay_success.html",
        )

        # 拼接支付宝登录链接
        # 响应登录支付宝连接
        # 真实环境电脑网站支付，需要跳转到https://openapi.alipay.com/gateway.do? + order_string
        # 沙箱环境电脑网站支付，需要跳转到https://openapi.alipaydev.com/gateway.do? + order_string
        alipay_url = settings.ALIPAY_URL + '?' + order_string

        # 响应支付宝登录链接
        return Response({'alipay_url': alipay_url})
