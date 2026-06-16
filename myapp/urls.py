from django.urls import path
from . import views

app_name = "house"

urlpatterns = [
    path("property/", views.property_list, name="property_list"),
    path("property/<int:pk>/", views.property_detail, name="property_detail"),

    path("predict/", views.ai_predict_form, name="ai_predict_form"),
    path("predict/result/", views.ai_predict_result, name="ai_predict_result"),
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("favorite/toggle/<int:pk>/", views.toggle_favorite, name="toggle_favorite"),
    path("favorite/list/", views.favorite_list_api, name="favorite_list_api"),
    path("favorite/delete/", views.favorite_delete_api, name="favorite_delete_api"),    
    path("favorite/status/", views.favorite_status_api, name="favorite_status_api"),
    path("speed-test/", views.speed_test, name="speed_test"),
]
