from django.shortcuts import render
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView

from .models import SKU
from .serializers import SKUSerializer, SKUIndexSerializer


# Create your views here.

# GET /categories/(?P<category_id>\d+)/skus?page=xxx&page_size=xxx&ordering=xxx
class SKUListView(ListAPIView):
    """商品列表视图"""

    # 指定排序的后端面:指定它是为了下面的ordering_fields
    filter_backends = [OrderingFilter]
    # 指定排序字段
    ordering_fields = ('create_time', 'price', 'sales')

    # 指定查询集
    # queryset = SKU.objects.all()
    def get_queryset(self):

        category_id = self.kwargs.get('category_id')  # 提取出url路径中的正则组的关键字参数
        return SKU.objects.filter(category_id=category_id, is_launched=True)

    # 指定序列化器
    serializer_class = SKUSerializer


from drf_haystack.viewsets import HaystackViewSet

class SKUSearchViewSet(HaystackViewSet):
    """
    SKU搜索
    """
    index_models = [SKU]

    serializer_class = SKUIndexSerializer