from drf_jsonapi.routers import Router

from .views import TrunkViewSet, LeafViewSet

router = Router(trailing_slash=False)
router.register(TrunkViewSet)
router.register(LeafViewSet)
urlpatterns = router.urls
