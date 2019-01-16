from rest_framework import serializers
from django_redis import get_redis_connection
import re
from rest_framework_jwt.settings import api_settings

from .models import User
from celery_tasks.email.tasks import send_verify_email
from .models import Address
from goods.models import SKU


class UserBrowseHistorySerializer(serializers.Serializer):
    """反序列化用户浏览记录"""
    sku_id = serializers.IntegerField(label='商品SKU编码', min_value=1)

    def validate_sku_id(self, value):
        """单独到sku_id进行额外校验"""
        try:
            SKU.objects.get(id=value)
        except SKU.DoesNotExist:
            raise serializers.ValidationError('sku id 不存在')

        # 能走到这里说明sku_id 商品存在
        return value

    def create(self, validated_data):
        """重写此方法就让把我们的浏览记录存到redis,不存到数据库"""

        # 取出sku_id
        sku_id = validated_data.get('sku_id')
        # 获取用户的id动态拼接当redis数据key
        user_id = self.context.get('request').user.id

        # 创建redis连接
        redis_conn = get_redis_connection('history')
        # 创建管道
        pl = redis_conn.pipeline()
        # 去重
        pl.lrem('history_%s' % user_id, 0, sku_id)

        # 添加
        pl.lpush('history_%s' % user_id, sku_id)

        # 截取
        pl.ltrim('history_%s' % user_id, 0, 4)

        # 执行管道
        pl.execute()

        return validated_data


class AddressTitleSerializer(serializers.ModelSerializer):
    """
    地址标题
    """

    class Meta:
        model = Address
        fields = ('title',)


class UserAddressSerializer(serializers.ModelSerializer):
    """
    用户地址序列化器
    """
    province = serializers.StringRelatedField(read_only=True)
    city = serializers.StringRelatedField(read_only=True)
    district = serializers.StringRelatedField(read_only=True)
    province_id = serializers.IntegerField(label='省ID', required=True)
    city_id = serializers.IntegerField(label='市ID', required=True)
    district_id = serializers.IntegerField(label='区ID', required=True)

    class Meta:
        model = Address
        exclude = ('user', 'is_deleted', 'create_time', 'update_time')

    def validate_mobile(self, value):
        """
        验证手机号
        """
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号格式错误')
        return value

    def create(self, validated_data):
        # 在序列化器中取到user并把它添加到反序列化之后的字典中
        validated_data['user'] = self.context['request'].user
        # 创建并保存地址中间就为了  地址关联用户
        address = Address.objects.create(**validated_data)

        return address


class EmailSerializer(serializers.ModelSerializer):
    """保存邮箱的序列化器"""

    class Meta:
        model = User
        fields = ['id', 'email']
        extra_kwargs = {
            'email': {
                'required': True
            }
        }

    def update(self, instance, validated_data):
        """重写此方法有两个目的: 1.只保存邮箱, 2.发激活邮件"""
        instance.email = validated_data.get('email')
        instance.save()  # ORM中 的保存
        # super(EmailSerializer, self).update(instance, validated_data)
        # 1.1 生成邮箱的激活链接
        verify_url = instance.generate_verify_email_url()
        # 2.发激活邮件
        # 传入收件人及激活链接
        send_verify_email.delay(instance.email, verify_url)

        return instance


class UserDetailSerializer(serializers.ModelSerializer):
    """用户详细信息序列化器"""

    class Meta:
        model = User
        fields = ['id', 'username', 'mobile', 'email', 'email_active']


class CreateUserSerializer(serializers.ModelSerializer):
    """注册序列化器"""

    password2 = serializers.CharField(label='确认密码', write_only=True)
    sms_code = serializers.CharField(label='短信验证码', write_only=True)
    allow = serializers.CharField(label='同意协议', write_only=True)
    token = serializers.CharField(label='token', read_only=True)

    # 所有字段: 'id', 'username', 'password', 'password2', 'mobile', 'sms_code', 'allow'
    # 模型中的字段: 'id', 'username', 'password', 'mobile'
    # 序列化(输出/响应出去) 'id', 'username', 'mobile'
    # 反序列化(输入/校验) 'username', 'password', 'password2', 'mobile', 'sms_code', 'allow'
    class Meta:
        model = User  # 序列化器中的字段从那个模型去映射
        fields = ['id', 'username', 'password', 'password2', 'mobile', 'sms_code', 'allow', 'token']
        extra_kwargs = {
            'username': {
                'min_length': 5,
                'max_length': 20,
                'error_messages': {
                    'min_length': '仅允许5-20个字符的用户名',
                    'max_length': '仅允许5-20个字符的用户名',
                }
            },
            'password': {
                'write_only': True,
                'min_length': 8,
                'max_length': 20,
                'error_messages': {
                    'min_length': '仅允许8-20个字符的密码',
                    'max_length': '仅允许8-20个字符的密码',
                }
            }
        }

    # 一定要注意下面代码的缩进问题
    def validate_mobile(self, value):
        """验证手机号"""
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号格式错误')
        return value

    def validate_allow(self, value):
        """检验用户是否同意协议"""
        if value != 'true':
            raise serializers.ValidationError('请同意用户协议')
        return value

    def validate(self, data):
        # 判断两次密码
        if data['password'] != data['password2']:
            raise serializers.ValidationError('两次密码不一致')

        # 判断短信验证码
        redis_conn = get_redis_connection('verify_codes')
        mobile = data['mobile']
        real_sms_code = redis_conn.get('sms_%s' % mobile)
        if real_sms_code is None:
            raise serializers.ValidationError('无效的短信验证码')
        if data['sms_code'] != real_sms_code.decode():
            raise serializers.ValidationError('短信验证码错误')

        return data

    # 重写create方法:把不需要存到数据库字段排除
    def create(self, validated_data):

        # 把不需要存到数据库中的字段删除
        del validated_data['password2']
        del validated_data['sms_code']
        del validated_data['allow']

        # 创建用户模型
        user = User(**validated_data)

        # 给密码进行加密处理并覆盖原有数据
        user.set_password(user.password)

        user.save()  # 保存到数据库

        # 'JWT_PAYLOAD_HANDLER':
        # 'rest_framework_jwt.utils.jwt_payload_handler',
        # __import__('rest_framework_jwt.utils.jwt_payload_handler')
        # token不要写在save前面,它不需要存到数据库中
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER  # 加载生成载荷函数
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER  # 加载进行生成token的函数

        payload = jwt_payload_handler(user)  # 通过传用用户信息进行生成载荷
        token = jwt_encode_handler(payload)  # 根据载荷内部再拿到内部的header 再取到SECRET_KEY 进行HS256加密最后把加它们拼接为完整的token
        user.token = token

        return user
