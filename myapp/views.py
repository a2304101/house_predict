from django.shortcuts import render
from django.http import HttpResponse
from datetime import datetime
from django.shortcuts import render, get_object_or_404
from django.db.models import Q, F
from .models import Property, City, District
from django.core.paginator import Paginator
from django.shortcuts import render
from .ml.feature_builder import build_predict_dataframe
from .ml.predictor import predict_price
from django.shortcuts import redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import FavoriteProperty
from django.http import JsonResponse
from .models import Property
import hashlib
import math
from django.core.cache import cache
import time
import json

CITY_GROUPS = {
    "北部": ["台北市", "新北市", "桃園市", "新竹市", "新竹縣", "宜蘭市", "宜蘭縣", "基隆市"],
    "中部": ["台中市", "彰化縣", "雲林縣", "苗栗縣", "南投縣"],
    "南部": ["高雄市", "台南市", "嘉義市", "嘉義縣", "屏東縣"],
    "東部": ["台東縣", "花蓮縣", "澎湖縣", "金門縣", "連江縣"],
}


def get_city_nav_data():
    cache_key = "property_city_nav:v2"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    cities = list(City.objects.all().order_by("name"))
    city_by_name = {city.name: city for city in cities}
    grouped_cities = [
        {
            "name": group_name,
            "cities": sorted(
                [city_by_name[name] for name in names if name in city_by_name],
                key=lambda city: city.name,
            ),
        }
        for group_name, names in CITY_GROUPS.items()
    ]

    data = (cities, grouped_cities)
    cache.set(cache_key, data, 3600)
    return data


def get_default_city_id():
    cache_key = "property_default_city_id:v1"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    default_city = (
        City.objects.filter(name="台北市").first()
        or City.objects.filter(name="臺北市").first()
        or City.objects.filter(name__contains="北").first()
        or City.objects.first()
    )
    city_id = str(default_city.id) if default_city else None
    cache.set(cache_key, city_id, 3600)
    return city_id


def get_district_options(city_id):
    cache_key = f"property_districts:{city_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    districts = list(District.objects.filter(city_id=city_id).order_by("name"))
    cache.set(cache_key, districts, 3600)
    return districts


def get_favorite_cache_version(user_id):
    cache_key = f"favorite_list_version:{user_id}"
    version = cache.get(cache_key)
    if version is None:
        version = 1
        cache.set(cache_key, version, None)
    return version


def bump_favorite_cache_version(user_id):
    cache_key = f"favorite_list_version:{user_id}"
    cache.add(cache_key, 1, None)
    try:
        cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 2, None)


# Create your views here.
def home(request):
    return HttpResponse("歡迎來到我的 Django 網站！目前時間是 " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
# def final(request):
#     if request.method == 'POST':
#         # 抓取表單資料
#         username = request.POST.get('username', '')
#         usersex = request.POST.get('usersex', 'male')
#         userschool = request.POST.get('userschool', '')
        
#         # 關鍵：核取方塊(Checkbox)是多選，必須使用 getlist
#         userinterest = request.POST.getlist('userinterest')
#         userthought = request.POST.get('userthought', '')
        
#         return render(request,"final_response.html",locals())
#     else:    
#         return render(request, 'final.html', locals())
# def bank(request):
#     result=""
#     account = BankAccount(5000, 1001)
#     print("目前餘額$", account.get_balance(), sep="")
#     result+="目前餘額$" + str(account.get_balance()) + "<br>"
#     print("提款金額 $10000 ...")
#     account.make_withdrawal(10000)
#     result+="提款金額 $10000 ...<br>"
#     print("重試提款 $1000 ...")
#     account.make_withdrawal(1000)
#     result+="重試提款 $1000 ...<br>"
#     print("儲蓄金額 $2000 ...")
#     result+="儲蓄金額 $2000 ...<br>"
#     account.make_deposit(2000)
#     print("現在餘額 $", account.get_balance(), sep="")
#     result+="現在餘額 $" + str(account.get_balance()) + "<br>"
#     account2 = BankAccount(10000, 1002)
#     account.transfer(3000, account2)
#     account.transfer(1000, account2)
#     print("目前餘額$", account.get_balance(), sep="")
#     result+="目前餘額$" + str(account.get_balance()) + "<br>"
#     return HttpResponse(result)
def final(request):
    return HttpResponse("歡迎來到我的 Django 網站！目前時間是 " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def property_list(request):
    if not request.user.is_authenticated:
        cache_key = "property_page_html:" + hashlib.md5(
            request.get_full_path().encode("utf-8")
        ).hexdigest()

        cached_html = cache.get(cache_key)
        if cached_html:
            return HttpResponse(cached_html)
            
    cities, grouped_cities = get_city_nav_data()
    # 縣市只能單選
    selected_city_id = request.GET.get("city")

    if not selected_city_id:
        selected_city_id = get_default_city_id()

    selected_district_ids = request.GET.getlist("district")

    # 資料來源預設 591 非預售
    selected_source_type = request.GET.get("source_type", "591_existing")

    selected_building_types = request.GET.getlist("building_type")
    selected_elevators = request.GET.getlist("elevator")

    # 預測比較：只能不選或單選
    predict_compare = request.GET.get("predict_compare")

    keyword = request.GET.get("keyword", "").strip()

    min_unit_price = request.GET.get("min_unit_price")
    max_unit_price = request.GET.get("max_unit_price")
    min_area = request.GET.get("min_area")
    max_area = request.GET.get("max_area")
    min_age = request.GET.get("min_age")
    max_age = request.GET.get("max_age")

    selects = [
        "location",
        "location__district",
        "location__district__city",
        "propertypredictionfeature",
    ]

    if selected_source_type == "591_existing":
        selects.append("house591existingdetail")
    elif selected_source_type == "591_presale":
        selects.append("house591presaledetail")
    elif selected_source_type in ["sinyi_existing", "sinyi_presale"]:
        selects.append("sinyidetail")

    qs = Property.objects.select_related(*selects)

    qs = qs.filter(is_training_valid=True)
    # 一定限制縣市
    qs = qs.filter(location__district__city_id=selected_city_id)
                     
    districts = get_district_options(selected_city_id)

    if selected_district_ids:
        qs = qs.filter(location__district_id__in=selected_district_ids)

    # 資料來源
    if selected_source_type == "591_existing":
        qs = qs.filter(source_type="591_existing")

    elif selected_source_type == "591_presale":
        qs = qs.filter(source_type="591_presale")

    elif selected_source_type == "history_existing":
        qs = qs.filter(source_type="history", is_presale=False)

    elif selected_source_type == "history_presale":
        qs = qs.filter(source_type="history", is_presale=True)
        
    elif selected_source_type == "sinyi_existing":
        qs = qs.filter(source_type="sinyi", is_presale=False,sinyidetail__isnull=False,)
        
    elif selected_source_type == "sinyi_presale":
        qs = qs.filter(source_type="sinyi", is_presale=True,sinyidetail__isnull=False,)  
              
    elif selected_source_type == "all":
        pass

    if selected_building_types:
        qs = qs.filter(building_type__in=selected_building_types)

    if selected_elevators:
        qs = qs.filter(elevator__in=selected_elevators)

    if keyword:
        keyword_filter = (
            Q(location__full_address__icontains=keyword)
            | Q(project_name__icontains=keyword)
            | Q(building_type__icontains=keyword)
        )

        if selected_source_type == "591_presale":
            keyword_filter |= Q(
                house591presaledetail__title__icontains=keyword
            )

        elif selected_source_type == "591_existing":
            keyword_filter |= (
                Q(house591existingdetail__title__icontains=keyword)
                | Q(house591existingdetail__community__icontains=keyword)
            )

        elif selected_source_type in ["sinyi_existing", "sinyi_presale"]:
            keyword_filter |= Q(
                sinyidetail__name__icontains=keyword
            )

        else:  # all
            keyword_filter |= (
                Q(house591presaledetail__title__icontains=keyword)
                | Q(house591existingdetail__title__icontains=keyword)
                | Q(house591existingdetail__community__icontains=keyword)
                | Q(sinyidetail__name__icontains=keyword)
            )
        qs = qs.filter(keyword_filter)
    if min_unit_price:
        qs = qs.filter(unit_price__gte=min_unit_price)

    if max_unit_price:
        qs = qs.filter(unit_price__lte=max_unit_price)

    if min_area:
        qs = qs.filter(area_ping__gte=min_area)

    if max_area:
        qs = qs.filter(area_ping__lte=max_area)

    if min_age:
        qs = qs.filter(building_age__gte=min_age)

    if max_age:
        qs = qs.filter(building_age__lte=max_age)

    # 單價 vs 預測
    if predict_compare == "unit_gt_predict":
        qs = qs.filter(
            propertypredictionfeature__prediction_price__isnull=False,
            unit_price__gt=F("propertypredictionfeature__prediction_price")
        )

    elif predict_compare == "unit_lt_predict":
        qs = qs.filter(
            propertypredictionfeature__prediction_price__isnull=False,
            unit_price__lt=F("propertypredictionfeature__prediction_price")
        )

    #qs = qs.order_by("-id")
    sort = request.GET.get("sort", "default")
    direction = request.GET.get("direction", "asc")

    if sort == "area":
        order_field = "area_ping"
    elif sort == "unit_price":
        order_field = "unit_price"
    elif sort == "age":
        order_field = "building_age"
    elif sort == "total_price":
        if selected_source_type == "591_existing":
            order_field = "house591existingdetail__total_price"
        elif selected_source_type in ["sinyi_existing", "sinyi_presale"]:
            order_field = "sinyidetail__total_price"            
        elif selected_source_type in ["history_existing", "history_presale"]:
            order_field = "unit_price"   # 歷史總價是 unit_price * area_ping，先用單價排序近似
        else:
            order_field = None        
    elif sort == "clicks":
        order_field = "sinyidetail__three_months_clicks"
    elif sort == "views":
        order_field = "house591existingdetail__views"  
    elif sort == "discount":
        order_field = "sinyidetail__discount"             
    else:
        order_field = None
    
    show_click_sort = selected_source_type in ["sinyi_existing", "sinyi_presale"]
    show_view_sort = selected_source_type == "591_existing"
    
    show_total_price_sort = selected_source_type in [
        "591_existing",
        "history_existing",
        "history_presale",
        "sinyi_existing",
        "sinyi_presale",   
    ]

    if order_field:
        qs = qs.order_by(order_field, "-id")
    else:
        # 💡 預設排序直接改成最新上架倒序，這會直接走主鍵（Primary Key）索引，速度極快！
        qs = qs.order_by("-id")
   
    PAGE_SIZE = 25

    page_number = request.GET.get("page", "1")
    try:
        page_number = int(page_number)
    except ValueError:
        page_number = 1

    if page_number < 1:
        page_number = 1

    count_cache_key = make_count_cache_key(request)
    total_count = cache.get(count_cache_key)

    if total_count is None:
        total_count = qs.count()
        cache.set(count_cache_key, total_count, 600)

    total_pages = math.ceil(total_count / PAGE_SIZE) if total_count else 1

    if page_number > total_pages:
        page_number = total_pages

    offset = (page_number - 1) * PAGE_SIZE

    properties = list(qs[offset:offset + PAGE_SIZE])

    has_previous = page_number > 1
    has_next = page_number < total_pages

    favorite_property_ids = set()
    if request.user.is_authenticated:
        favorite_property_ids = set(
            FavoriteProperty.objects.filter(
                user=request.user,
                property_id__in=[p.id for p in properties]
            ).values_list("property_id", flat=True)
        )
         
    for p in properties:
        floor = p.transfer_floor

        if floor:
            floor = str(floor)
            floor = floor.replace(".0", "")
            floor = floor.replace(",", "-")
            p.transfer_floor_display = floor
        else:
            p.transfer_floor_display = "-"

            
    query_params = request.GET.copy()
    query_params.pop("page", None)
    query_params.pop("sort", None)
    query_params.pop("direction", None)
    
    building_type_options = [
        "住宅大樓(11層含以上有電梯)",
        "透天厝",
        "華廈(10層含以下有電梯)",
        "公寓(5樓含以下無電梯)",
        "其他",
        "套房(1房1廳1衛)",
    ]

    source_type_options = [
        ("all", "全部"),
        ("591_existing", "591非預售"),
        ("591_presale", "591預售"),
        ("history_existing", "歷史非預售屋"),
        ("history_presale", "歷史預售屋"),
        ("sinyi_existing", "信義非預售"),
        ("sinyi_presale", "信義預售"),
    ]
    start_page = max(page_number - 3, 1)
    end_page = min(page_number + 3, total_pages)

    page_range = range(start_page, end_page + 1)
    context = {
        "cities": cities,
        "grouped_cities": grouped_cities,
        "districts": districts,

        "properties": properties,
        "total_count": total_count,
        "total_pages": total_pages,
        "page_number": page_number,
        "has_previous": has_previous,
        "has_next": has_next,
        #"page_range": range(1, total_pages + 1),
        "page_range": page_range,
        "sort": sort,
        "direction": direction,
    
        "selected_city_id": selected_city_id,
        "selected_district_ids": selected_district_ids,
        "selected_source_type": selected_source_type,
        "selected_building_types": selected_building_types,
        "selected_elevators": selected_elevators,
        "predict_compare": predict_compare,

        "building_type_options": building_type_options,
        "source_type_options": source_type_options,

        "request_get": request.GET,
        "querystring": query_params.urlencode(),
        
        "show_click_sort": show_click_sort,
        "show_view_sort": show_view_sort,
        
        "show_total_price_sort": show_total_price_sort,
        "favorite_property_ids": favorite_property_ids,
    }

    response = render(request, "house/property_list.html", context)

    if not request.user.is_authenticated:
        cache.set(cache_key, response.content, 300)

    return response

def property_detail(request, pk):
    cache_key = f"property_detail_data:{pk}"
    cached = cache.get(cache_key)

    if cached:
        prop = cached["prop"]
        existing_detail = cached["existing_detail"]
        presale_detail = cached["presale_detail"]
        history_detail = cached["history_detail"]
        sinyi_detail = cached["sinyi_detail"]
        poi = cached["poi"]
        prediction = cached["prediction"]

    else:
        prop = get_object_or_404(
            Property.objects.select_related(
                "location",
                "location__district",
                "location__district__city",
                "propertypredictionfeature",
                "propertypoifeature",
                "sinyidetail",
            ),
            pk=pk,
            is_training_valid=True,
        )

        existing_detail = getattr(prop, "house591existingdetail", None)
        presale_detail = getattr(prop, "house591presaledetail", None)
        history_detail = getattr(prop, "historytransactiondetail", None)
        sinyi_detail = getattr(prop, "sinyidetail", None)
        poi = getattr(prop, "propertypoifeature", None)
        prediction = getattr(prop, "propertypredictionfeature", None)

        cache.set(cache_key, {
            "prop": prop,
            "existing_detail": existing_detail,
            "presale_detail": presale_detail,
            "history_detail": history_detail,
            "sinyi_detail": sinyi_detail,
            "poi": poi,
            "prediction": prediction,
        }, 300)

    is_favorited = False

    if request.user.is_authenticated:
        is_favorited = FavoriteProperty.objects.filter(
            user=request.user,
            property_id=pk,
        ).exists()

    context = {
        "prop": prop,
        "existing_detail": existing_detail,
        "presale_detail": presale_detail,
        "history_detail": history_detail,
        "poi": poi,
        "prediction": prediction,
        "sinyi_detail": sinyi_detail,
        "is_favorited": is_favorited,
    }

    return render(request, "house/property_detail.html", context)

def build_querystring(request, page=None):
    query = request.GET.copy()

    if page is not None:
        query["page"] = page

    return query.urlencode()

def ai_predict_form(request):
    cities = City.objects.all().order_by("name")

    selected_city_id = request.GET.get("city")

    if selected_city_id:
        selected_city = City.objects.filter(id=selected_city_id).first()
    else:
        selected_city = (
            City.objects.filter(name="台北市").first()
            or City.objects.filter(name="臺北市").first()
            or City.objects.first()
        )

    districts = District.objects.none()

    if selected_city:
        districts = District.objects.filter(
            city=selected_city
        ).order_by("name")

    building_type_options = [
        "住宅大樓(11層含以上有電梯)",
        "華廈(10層含以下有電梯)",
        "公寓(5樓含以下無電梯)",
        "透天厝",
        "其他",
        "套房(1房1廳1衛)",
    ]

    return render(request, "house/ai_predict_form.html", {
        "cities": cities,
        "districts": districts,
        "selected_city": selected_city,
        "building_type_options": building_type_options,
    })

def ai_predict_result(request):
    req_t0 = time.time()
    print("=== AI START ===", flush=True)

    if request.method != "POST":
        return redirect("house:ai_predict_form")

    post_data = request.POST.copy()

    print("after post copy:", round(time.time() - req_t0, 4), flush=True)

    city_obj = City.objects.filter(id=post_data.get("city")).first()

    print("after city query:", round(time.time() - req_t0, 4), flush=True)

    if city_obj:
        post_data["city"] = city_obj.name

    cache_source = {
        key: post_data.get(key)
        for key in sorted(post_data.keys())
        if key != "csrfmiddlewaretoken"
    }

    cache_raw = json.dumps(
        cache_source,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )

    cache_key = "ai_predict_result:" + hashlib.md5(
        cache_raw.encode("utf-8")
    ).hexdigest()

    cached_context = cache.get(cache_key)

    print("after result cache get:", round(time.time() - req_t0, 4), flush=True)

    if cached_context:
        print("=== RESULT CACHE HIT ===", flush=True)

        cached_context["from_cache"] = True

        t6 = time.time()
        response = render(request, "house/ai_predict_result.html", cached_context)

        print("render(cache):", round(time.time() - t6, 4), flush=True)
        print("TOTAL:", round(time.time() - req_t0, 4), flush=True)

        return response

    print("=== RESULT CACHE MISS ===", flush=True)
    print("=== BEFORE BUILD DF ===", flush=True)

    t_build = time.time()

    (
        df,
        clean_info,
        geo_info,
        poi_features,
        area_price_match_level,
    ) = build_predict_dataframe(post_data)

    print("build total:", round(time.time() - t_build, 4), flush=True)
    print("=== AFTER BUILD DF ===", flush=True)

    print("before predict:", round(time.time() - req_t0, 4), flush=True)

    t5 = time.time()
    prediction_price = predict_price(df)

    print("predict:", round(time.time() - t5, 4), flush=True)

    input_data = df.iloc[0].to_dict()

    area = input_data["坪數"]
    area_last_month_price = input_data["area_last_month_price"]

    estimated_total_price = prediction_price * area

    if area_last_month_price:
        area_diff_pct = (
            (prediction_price - area_last_month_price)
            / area_last_month_price
            * 100
        )
    else:
        area_diff_pct = None

    context = {
        "prediction_price": prediction_price,
        "estimated_total_price": estimated_total_price,
        "area_last_month_price": area_last_month_price,
        "area_diff_pct": area_diff_pct,
        "area_price_match_level": area_price_match_level,
        "input_data": input_data,
        "clean_info": clean_info,
        "geo_info": geo_info,
        "poi_features": poi_features,
        "from_cache": False,
    }

    cache.set(cache_key, context, 3600)

    print("after result cache set:", round(time.time() - req_t0, 4), flush=True)

    t6 = time.time()
    response = render(request, "house/ai_predict_result.html", context)

    print("render:", round(time.time() - t6, 4), flush=True)
    print("TOTAL:", round(time.time() - req_t0, 4), flush=True)

    return response

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            messages.success(request, "登入成功")
            return redirect("house:property_list")

        messages.error(request, "無此帳號或密碼錯誤")

    return render(request, "house/login.html")


def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        if User.objects.filter(username=username).exists():
            messages.error(request, "帳號已存在")
            return render(request, "house/register.html")

        User.objects.create_user(username=username, password=password)
        messages.success(request, "註冊成功，請登入")
        return redirect("house:login")

    return render(request, "house/register.html")


def logout_view(request):
    logout(request)
    return redirect("house:property_list")

@require_POST
def toggle_favorite(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "未登入，請先登入"}, status=401)

    if not Property.objects.filter(pk=pk).exists():
        return JsonResponse({"ok": False, "message": "找不到物件"}, status=404)

    fav, created = FavoriteProperty.objects.get_or_create(
        user=request.user,
        property_id=pk,
    )

    if created:
        bump_favorite_cache_version(request.user.id)
        return JsonResponse({"ok": True, "favorited": True, "message": "已加入收藏"})

    fav.delete()
    bump_favorite_cache_version(request.user.id)
    return JsonResponse({"ok": True, "favorited": False, "message": "已取消收藏"})

def get_property_card_data(p):
    title = p.project_name or p.location.full_address
    image = ""
    total_price = ""

    existing = getattr(p, "house591existingdetail", None)
    presale = getattr(p, "house591presaledetail", None)
    sinyi = getattr(p, "sinyidetail", None)
    pred = getattr(p, "propertypredictionfeature", None)

    if p.source_type == "591_existing" and existing:
        title = existing.title or title
        image = existing.photo or ""
        total_price = existing.total_price or ""

    elif p.source_type == "591_presale" and presale:
        title = presale.title or title
        total_price = presale.total_price_range or ""

    elif p.source_type == "sinyi" and sinyi:
        title = sinyi.name or title
        image = sinyi.large_image or ""
        total_price = sinyi.total_price or ""

    elif p.source_type == "history":
        if p.unit_price and p.area_ping:
            total_price = round(p.unit_price * p.area_ping)

    return {
        "id": p.id,
        "url": f"/property/{p.id}/",
        "source_type": p.source_type,
        "is_presale": p.is_presale,
        "title": title[:24] + "..." if len(title) > 24 else title,
        "image": image,
        "total_price": total_price,
        "unit_price": round(p.unit_price, 2) if p.unit_price else "",
        "prediction_price": round(pred.prediction_price, 2) if pred and pred.prediction_price else "",
        "area": round(p.area_ping, 2) if p.area_ping else "",
    }



def favorite_list_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({
            "ok": False,
            "message": "未登入",
            "items": [],
        }, status=401)

    group = request.GET.get("group", "591")
    presale = request.GET.get("presale", "0")
    sort = request.GET.get("sort", "default")
    version = get_favorite_cache_version(request.user.id)
    cache_key = f"favorite_list:{request.user.id}:{version}:{group}:{presale}:{sort}"
    cached_items = cache.get(cache_key)

    if cached_items is not None:
        return JsonResponse({
            "ok": True,
            "items": cached_items,
        })

    qs = FavoriteProperty.objects.filter(
        user=request.user
    ).select_related(
        "property",
        "property__location",
        "property__location__district",
        "property__location__district__city",
        "property__propertypredictionfeature",
        "property__house591existingdetail",
        "property__house591presaledetail",
        "property__sinyidetail",
    )
    
    if group == "591":
        if presale == "1":
            qs = qs.filter(property__source_type="591_presale")
        else:
            qs = qs.filter(property__source_type="591_existing")

    elif group == "history":
        qs = qs.filter(property__source_type="history", property__is_presale=(presale == "1"))

    elif group == "sinyi":
        qs = qs.filter(property__source_type="sinyi", property__is_presale=(presale == "1"))

    if sort == "unit_asc":
        qs = qs.order_by("property__unit_price")
    elif sort == "unit_desc":
        qs = qs.order_by("-property__unit_price")
    elif sort == "area_asc":
        qs = qs.order_by("property__area_ping")
    elif sort == "area_desc":
        qs = qs.order_by("-property__area_ping")
    else:
        qs = qs.order_by("-created_at")

    items = [get_property_card_data(fav.property) for fav in qs[:100]]
    cache.set(cache_key, items, 60)

    return JsonResponse({
        "ok": True,
        "items": items,
    })
    
@require_POST
def favorite_delete_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "未登入"}, status=401)

    ids = request.POST.getlist("ids[]")

    deleted_count, _ = FavoriteProperty.objects.filter(
        user=request.user,
        property_id__in=ids
    ).delete()

    if deleted_count:
        bump_favorite_cache_version(request.user.id)

    return JsonResponse({"ok": True})

def favorite_status_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({
            "ok": False,
            "favorite_ids": [],
        })

    ids = request.GET.get("ids", "")
    ids = [int(x) for x in ids.split(",") if x.isdigit()]

    favorite_ids = list(
        FavoriteProperty.objects.filter(
            user=request.user,
            property_id__in=ids
        ).values_list("property_id", flat=True)
    )

    return JsonResponse({
        "ok": True,
        "favorite_ids": favorite_ids,
    })
    
def speed_test(request):
    ids = list(
        Property.objects
        .filter(is_training_valid=True)
        .values_list("id", flat=True)[:25]
    )
    return JsonResponse({"count": len(ids), "ids": ids})
    
def make_count_cache_key(request):
    params = request.GET.copy()

    # page 不影響總筆數，所以拿掉
    params.pop("page", None)

    raw = params.urlencode()

    key_hash = hashlib.md5(raw.encode("utf-8")).hexdigest()

    return f"property_count:{key_hash}"
