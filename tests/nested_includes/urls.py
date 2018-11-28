from rest_framework_nested import routers

from .views import TrunkViewSet, LeafViewSet

router = routers.DefaultRouter(trailing_slash=False)
router.register("trunks", TrunkViewSet, base_name="trunks")
router.register("leaves", LeafViewSet, base_name="leaves")
urlpatterns = router.urls
