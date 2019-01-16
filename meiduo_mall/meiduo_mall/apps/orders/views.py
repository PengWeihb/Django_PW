from decimal import Decimal
from django_redis import get_redis_connection
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView

from goods.models import SKU
from orders.serializers import OrderSettlementSerializer, CommitOrderSerializer

# url(r'^orders/$', views.CommitOrderView.as_view())
class CommitOrderView(CreateAPIView):
    """提交订单:保存订单及订单商品数据"""
    # 表示只有登录用户才能访问此接口
    permission_classes = [IsAuthenticated]
    # 指定序列化器
    serializer_class = CommitOrderSerializer


#     url(r'^orders/settlement/$', views.OrderSettlementView.as_view()),
class OrderSettlementView(APIView):
    """
    订单结算
    """
    # 表示只有登录用户才能访问此接口
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        获取
        """
        user = request.user

        # 从购物车中获取用户勾选要结算的商品信息
        redis_conn = get_redis_connection('carts')
        # {'sku_id1': 2, 'sku_id2': 5}
        redis_cart = redis_conn.hgetall('cart_%s' % user.id)
        # {'sku_id1'}
        cart_selected = redis_conn.smembers('selected_%s' % user.id)

        # 核心下三行是核心代码
        cart = {}
        for sku_id in cart_selected:  # 只要勾选的商品数据
            cart[int(sku_id)] = int(redis_cart[sku_id])

        # 查询商品信息
        skus = SKU.objects.filter(id__in=cart.keys())
        for sku in skus:
            sku.count = cart[sku.id]

        # 运费
        freight = Decimal('10.00')

        serializer = OrderSettlementSerializer({'freight': freight, 'skus': skus})
        return Response(serializer.data)
