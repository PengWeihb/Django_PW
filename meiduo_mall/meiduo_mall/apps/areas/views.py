from django.shortcuts import render
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_extensions.mixins import CacheResponseMixin

from .models import Area
from .serializers import AreasSerializer, SubsAreasSerializer


# Create your views here.
class AreasViewSet(CacheResponseMixin, ReadOnlyModelViewSet):
    """返回省市区数据"""

    pagination_class = None  # 禁用分页
    # 指定查询集
    # queryset = Area.objects.all()
    def get_queryset(self):

        # bj = Area.objects.get(id=110000)
        # bjxmdsycity = bj.subs.all()
        # bjcity = bjxmdsycity.fitler(name='北京市')
        # bjxmdsyqu = bjcity.subs.all()
        # # bjs = bjcity.praent
        # 重写此方法来返回指定的查询集
        if self.action == 'list':  # 如果是list行为表示它要获取所有省
            return Area.objects.filter(parent=None)
        else:
            return Area.objects.all()

    # 指定序列化器
    # serializer_class = AreasSerializer
    def get_serializer_class(self):
        # 重写此方法返回指定的序列化器
        if self.action == 'list':
            return AreasSerializer
        else:
            return SubsAreasSerializer