import os
import django
import requests
import re
from bs4 import BeautifulSoup

# 1. 初始化 Django 環境 (讓腳本能直接存取 MySQL)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'final.settings') # 替換成你的專案名
django.setup()

from myapp.models import Product, Platform, PriceRecord # 替換成你的 App 名