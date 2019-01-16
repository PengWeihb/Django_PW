from django.contrib import admin

from . import models
from celery_tasks.html.tasks import generate_static_list_search_html, generate_static_sku_detail_html


class SKUAdmin(admin.ModelAdmin):
    """SKU模型监听它的保存后生成商品静态html"""

    def save_model(self, request, obj, form, change):
        """
        当GoodsCategory模型的数据在admin中做了保存操作,就会自动调用此方法
        :param request: 本次保存时的请求对象
        :param obj:  本次要保存的模型对象
        :param form: 本次执行保存时的表单信息
        :param change: 本次保存时和之前数据的变化
        :return: None
        """
        obj.save()
        # 保存完之后立即去重新生成(sku_id).html静态文件
        generate_static_sku_detail_html.delay(obj.id)


class SKUImageAdmin(admin.ModelAdmin):
    """SKU图片保存和删除后重新生成商品静态html"""

    def save_model(self, request, obj, form, change):
        """
        当GoodsCategory模型的数据在admin中做了保存操作,就会自动调用此方法
        :param request: 本次保存时的请求对象
        :param obj:  本次要保存的模型对象
        :param form: 本次执行保存时的表单信息
        :param change: 本次保存时和之前数据的变化
        :return: None
        """
        sku = obj.sku  # 取出sku
        if not sku.default_image_url:  # 判断sku里面的有没有默认图片
            sku.default_image_url = obj.image.url  # 没有就给它设置一个默认
            sku.save()  # 更新sku商品默认图片
        obj.save()


        # 保存完之后立即去重新生成(sku_id).html静态文件
        generate_static_list_search_html.delay(obj.sku.id)

    def delete_model(self, request, obj):
        """
        当GoodsCategory模型的数据在admin中做了删除操作,就会自动调用此方法
        :param request: 本次删除时的请求对象
        :param obj:  本次要删除的模型对象
        :return:  None
        """
        obj.delete()
        # 删除之后立即去重新生成list.html静态文件
        generate_static_list_search_html.delay(obj.sku.id)


# Register your models here.
class GoodsCategoryAdmin(admin.ModelAdmin):
    """自定义站点管理类,用来监听保存和删除事件"""

    def save_model(self, request, obj, form, change):
        """
        当GoodsCategory模型的数据在admin中做了保存操作,就会自动调用此方法
        :param request: 本次保存时的请求对象
        :param obj:  本次要保存的模型对象
        :param form: 本次执行保存时的表单信息
        :param change: 本次保存时和之前数据的变化
        :return: None
        """
        obj.save()
        # 保存完之后立即去重新生成list.html静态文件
        generate_static_list_search_html.delay()

    def delete_model(self, request, obj):
        """
        当GoodsCategory模型的数据在admin中做了删除操作,就会自动调用此方法
        :param request: 本次删除时的请求对象
        :param obj:  本次要删除的模型对象
        :return:  None
        """
        obj.delete()
        # 删除之后立即去重新生成list.html静态文件
        generate_static_list_search_html.delay()


admin.site.register(models.GoodsCategory, GoodsCategoryAdmin)
admin.site.register(models.GoodsChannel)
admin.site.register(models.Goods)
admin.site.register(models.Brand)
admin.site.register(models.GoodsSpecification)
admin.site.register(models.SpecificationOption)
admin.site.register(models.SKU, SKUAdmin)
admin.site.register(models.SKUSpecification)
admin.site.register(models.SKUImage, SKUImageAdmin)
