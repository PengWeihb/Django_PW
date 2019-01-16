from django.db import models

# Create your models here.

class Area(models.Model):
    """
    行政区划
    """
    name = models.CharField(max_length=20, verbose_name='名称')  # related_name自定义反向关联模型中的字段名 在一的那方会有一个多的外键:默认一的那方法看到的多的那个外键多的模型类型名小写_set
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, related_name='subs', null=True, blank=True, verbose_name='上级行政区划')

    class Meta:
        db_table = 'tb_areas'
        verbose_name = '行政区划'
        verbose_name_plural = '行政区划'

    def __str__(self):
        return self.name