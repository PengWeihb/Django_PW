from django.shortcuts import render
from rest_framework.views import APIView
from django_redis import get_redis_connection
from rest_framework.response import Response
from rest_framework import status
import pickle, base64

# Create your views here.
from carts.serializers import CartSerializer, CartSKUSerializer, CartDeleteSeriazlier, CartSelectedAllSerializer
from goods.models import SKU

class CartSelectedAllView(APIView):
    """购物车全选视图"""

    def perform_authentication(self, request):
        """默认视图在进行请求分发时就会进行认证
        在视图中重写此方法,如果内部直接pass,表示在请求分发时,先不要认证,让请求可以正常访问
        目的:延后它的认证,为了让未登录用户也能先访问我的视图
        将来自己去写认证,
        """
        pass


    def put(self, request):

        # 创建序列化器(进行反序列化)对前端传过来的是否全选数据进行校验
        serializer = CartSelectedAllSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 获取校验后面selected数据
        selected = serializer.validated_data.get('selected')

        try:
            user = request.user
        except Exception:
            user = None

        if user is not None and user.is_authenticated:  # 判断当前是不是登录用户
            # 登录用户,操作redis购物车
            redis_conn = get_redis_connection('carts')
            # 获取购物车商品数据
            redis_cart_dict = redis_conn.hgetall('cart_%s' % user.id)
            sku_id_keys = redis_cart_dict.keys()  # 取出字典中所有的key
            if selected:  # 成立表示要全选
                redis_conn.sadd('selected_%s' % user.id, *sku_id_keys)
            else:  # 全部不勾选
                redis_conn.srem('selected_%s' % user.id, *sku_id_keys)
            # 响应
            return Response(serializer.data)
        else:
            # 未登录用户,操作cookie购物车
            cart_str = request.COOKIES.get('cart')
            if cart_str:  # 判断cookie是否有值
                cookie_cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                cookie_cart_dict = {}
                """
                {
                    sku_id_1: {
                        'count': count,
                        'selected: True
                    },
                    sku_id_2: {
                        'count': count,
                        'selected: True
                    }
                }
                """

            for sku_dict in cookie_cart_dict.values():
                sku_dict['selected'] = selected  # 拿到里面的每个小字典,把它们的selected改成全选或全部不选

            # 把购物车字典转换成购物车字符串
            cookie_cart_str = base64.b64encode(pickle.dumps(cookie_cart_dict)).decode()
            # 创建响应对象
            response = Response(serializer.data)
            # 设置cookie
            response.set_cookie('cart', cookie_cart_str)
            return response





class CartView(APIView):
    """购物车视图:增删改查"""

    def perform_authentication(self, request):
        """默认视图在进行请求分发时就会进行认证
        在视图中重写此方法,如果内部直接pass,表示在请求分发时,先不要认证,让请求可以正常访问
        目的:延后它的认证,为了让未登录用户也能先访问我的视图
        将来自己去写认证,
        """
        pass

    def post(self, request):
        """增加购物车"""

        # 创建序列序列器,进行反序列化
        serializer = CartSerializer(data=request.data)
        # 校验数据
        serializer.is_valid(raise_exception=True)

        # 取出校验之后的数据
        sku_id = serializer.validated_data.get('sku_id')
        count = serializer.validated_data.get('count')
        selected = serializer.validated_data.get('selected')

        try:
            user = request.user
        except Exception:
            user = None

        if user is not None and user.is_authenticated:  # 判断当前是不是登录用户
            # 如果当前是登录用户我们操作redis购物车
            # 获取到连接redis的对象
            redis_conn = get_redis_connection('carts')
            # 创建管道
            pl = redis_conn.pipeline()
            # cart_user_idA : {sku_id1: count, sku_id2: count}
            # cart_user_idB : {sku_id1: count, sku_id2: count}
            # hincrby(name, key, amount=1)  此方法如果要添加的key在原哈希中不存就是新增,如果key已经存在,就后面的value和原有value相加
            pl.hincrby('cart_%s' % user.id, sku_id, count)

            # 用哈希来存商品及它的数量
            # card_dict = redis_conn.hgetall('cart_%s' % user.id)
            # if sku_id in card_dict:
            #     origin_count = card_dict[sku_id]
            #     count = origin_count + count

            # 用set来存商品是否被勾选
            # {'skuid1'}
            if selected:
                # sadd(name, *values)
                pl.sadd('selected_%s' % user.id, sku_id)
            # 执行管道
            pl.execute()

            # 响应
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            # 未登录用户操作cookie购物车

            # 获取cookie中原有的购物车数据
            cookie_str = request.COOKIES.get('cart')
            if cookie_str:
                # 把cookie_str转换成python中的标准字典
                # 把cookie_str字符串转换成cookie_str_bytes
                cookie_str_bytes = cookie_str.encode()

                # 把cookie_str_bytes用b64转换为cookie_dict_bytes类型
                cookie_dict_bytes = base64.b64decode(cookie_str_bytes)

                # cookie_dict_bytes类型转换成Python中标准的字典
                cart_dict = pickle.loads(cookie_dict_bytes)
                # cart_dict = pickle.loads(base64.decode(cookie_str.encode()))

                # 判断当前要新加入购物车的sku_id是否在原cookie中已存,如果存在,做增量,不存在新加入字典中
                if sku_id in cart_dict:
                    # 如果if成立说明新增的商品购物车中已存在
                    origin_count = cart_dict[sku_id]['count']
                    count += origin_count  #  count = origin_count + count
            else:  # 第一次来添加到cookie购物车
                cart_dict = {}

            # 不管之前有没有这个商品都重新包一下
            cart_dict[sku_id] = {
                'count': count,
                'selected': selected

            }

            # 把cart_dict 转换成cookie_str类型
            # 把Python的字典转换成cookie_dict_bytes字典的bytes类型
            cookie_dict_bytes = pickle.dumps(cart_dict)
            # 把cookie_dict_bytes字典的bytes类型转换成cookie_str_bytes字符串类型的bytes
            cookie_str_bytes = base64.b64encode(cookie_dict_bytes)
            # 把cookie_str_bytes类型转换成字符串
            cookie_str = cookie_str_bytes.decode()


            # 把cookie写入到浏览器
            # 创建响应对象
            response = Response(serializer.data, status=status.HTTP_201_CREATED)
            # 设置cookies
            response.set_cookie('cart', cookie_str)
            # 响应
            return response



    def get(self, request):
        """查询购物车"""

        # 获取user
        try:
            user = request.user
        except Exception:
            user = None

        if user is not None and user.is_authenticated:
            # 登录用户从redis中获取数据
            # 获取redis的连接对象
            redis_conn = get_redis_connection('carts')

            # 取出哈希数据cart_user_id {sku_id1: count, sku_id2: count}
            redis_cart = redis_conn.hgetall('cart_%s' % user.id)

            # 取出set数据 {sku_id1, sku_id2}
            selected_cart = redis_conn.smembers('selected_%s' % user.id)

            card_dict = {}
            # Python3中redis取出来的数据内部都是bytes类型
            for sku_id, count in redis_cart.items():
                card_dict[int(sku_id)] = {
                    'count': int(count),
                    # True if sku_id in selected_cart else False
                    'selected': sku_id in selected_cart  # 判断当前的sku_id是否在set无序集体中,如果存在说明它是勾选
                }

            """ 
            为了方便后续redis数据和cookie数据进行统一的转换,现在把redis中的数据先转的和cookie中的字典数据格式一样
            {
                sku_id_1: {
                    'count': count,
                    'selected: True
                },
                sku_id_2: {
                    'count': count,
                    'selected: True
                }
            }
            """


        else:
            # 未登录用户从cookie中获取数据
            cookie_cart = request.COOKIES.get('cart')
            if cookie_cart:
                # 把cookie字符串购物车数据转换到Python字典类型
                cookie_cart_str_bytes = cookie_cart.encode()
                cookie_cart_dict_bytes = base64.b64decode(cookie_cart_str_bytes)
                card_dict = pickle.loads(cookie_cart_dict_bytes)
            else:
                card_dict = {}

        card_list = []
        for sku_id in card_dict:
            sku = SKU.objects.get(id=sku_id)
            # 给模型多绑定两个属性
            sku.count = card_dict[sku_id]['count']
            sku.selected = card_dict[sku_id]['selected']
            card_list.append(sku)
        # 只能把模型或列表里面装的模型进行序列化
        serializer = CartSKUSerializer(card_list, many=True)
        return Response(serializer.data)


    def put(self, request):
        """修改购物车"""
        # 创建序列序列器,进行反序列化
        serializer = CartSerializer(data=request.data)
        # 校验数据
        serializer.is_valid(raise_exception=True)

        # 取出校验之后的数据
        sku_id = serializer.validated_data.get('sku_id')
        count = serializer.validated_data.get('count')
        selected = serializer.validated_data.get('selected')

        try:
            user = request.user
        except Exception:
            user = None

        if user is not None and user.is_authenticated:  # 判断当前是不是登录用户
            # 如果当前是登录用户我们操作redis购物车
            # 获取到连接redis的对象
            redis_conn = get_redis_connection('carts')
            # 创建管道
            pl = redis_conn.pipeline()
            # hset(name, key, value)
            pl.hset('cart_%s' % user.id, sku_id, count)  # 修改原有商品的数据
            # 修改商品的勾选状态
            if selected:
                pl.sadd('selected_%s' % user.id, sku_id)  # 如果当前商品从未勾选变成了勾选就把这的sku_id加入到set无序集合
            else:
                pl.srem('selected_%s' % user.id, sku_id)  # 如果当前商品从勾选变成了未勾选,就把它的sku_id从set无序集合中删除
            # 执行管道
            pl.execute()
            return Response(serializer.data)
        else:
            # 未登录用户操作cookie购物车
            # 获取cookie中原有的购物车数据
            cookie_str = request.COOKIES.get('cart')
            if cookie_str:
                # 把cookie_str转换成python中的标准字典
                # 把cookie_str字符串转换成cookie_str_bytes
                cookie_str_bytes = cookie_str.encode()

                # 把cookie_str_bytes用b64转换为cookie_dict_bytes类型
                cookie_dict_bytes = base64.b64decode(cookie_str_bytes)

                # cookie_dict_bytes类型转换成Python中标准的字典
                cart_dict = pickle.loads(cookie_dict_bytes)
                # cart_dict = pickle.loads(base64.decode(cookie_str.encode()))

            else:  # 第一次来添加到cookie购物车
                cart_dict = {}

            # 不管之前有没有这个商品都重新包一下
            cart_dict[sku_id] = {
                'count': count,
                'selected': selected

            }

            # 把cart_dict 转换成cookie_str类型
            # 把Python的字典转换成cookie_dict_bytes字典的bytes类型
            cookie_dict_bytes = pickle.dumps(cart_dict)
            # 把cookie_dict_bytes字典的bytes类型转换成cookie_str_bytes字符串类型的bytes
            cookie_str_bytes = base64.b64encode(cookie_dict_bytes)
            # 把cookie_str_bytes类型转换成字符串
            cookie_str = cookie_str_bytes.decode()

            # 把cookie写入到浏览器
            # 创建响应对象
            response = Response(serializer.data)
            # 设置cookies
            response.set_cookie('cart', cookie_str)
            # 响应
            return response


    def delete(self, request):
        """删除购物车"""
        # 创建序列化器(反序列化校验前端传入的sku_id)
        serializer = CartDeleteSeriazlier(data=request.data)
        serializer.is_valid(raise_exception=True)
        # 把校验后的sku_id取出来
        sku_id = serializer.validated_data.get('sku_id')

        # 获取user
        try:
            user = request.user
        except Exception:
            user = None
        # 创建响应对象
        response = Response(status=status.HTTP_204_NO_CONTENT)
        if user is not None and user.is_authenticated:
            # 登录用户操作redis购物车
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()
            # 先把redis中购物车商品数据删除(以下两行是核心代码)
            pl.hdel('cart_%s' % user.id, sku_id)
            # 删除当前商品勾选状态
            pl.srem('selected_%s' % user.id, sku_id)
            pl.execute()  # 执行管道

        else:
            # 未登录用户操作cookie购物车
            cart_str = request.COOKIES.get('cart')
            if cart_str:  # 判断cookie是否有值
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                cart_dict = {}

            if sku_id in cart_dict:
                del cart_dict[sku_id]  # 把要删除的商品从字典中删除

                if len(cart_dict.keys()):  # 判断字典中是否还有数据

                    cookie_cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()

                    response.set_cookie('cart', cookie_cart_str)
                else:
                    response.delete_cookie('cart')  # 删除cookie中的购物车数据

        return response

