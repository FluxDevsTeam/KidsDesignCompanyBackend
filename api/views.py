import uuid
from django.db.models import Q
from django.utils import timezone
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_201_CREATED
from django.db.models import F

from .permissions import *
from django.conf import settings
from django.shortcuts import render
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import viewsets, status
from .seralizers import *


def initiate_payment(amount, email, pending_id, user):
    url = "https://api.flutterwave.com/v3/payments"
    headers = {
        "Authorization": f"Bearer {settings.FLW_SEC_KEY}"
    }
    first_name = user.first_name
    last_name = user.last_name
    data = {
        "tx_ref": str(uuid.uuid4()),
        "amount": str(amount),
        "currency": "NGN",
        "redirect_url": "http:/127.0.0.1:8000/api/pending/confirm_payment/?p_id=" + pending_id,
        "meta": {
            "consumer_id": 23,
            "consumer_mac": "92a3-912ba-1192a"
        },
        "customer": {
            "email": email,
            "phonenumber": "080****4528",
            "name": f"{last_name} {first_name}"
        },
        "customizations": {
            "title": "Success Air",
            "logo": "https://jetinternational.com/wp-content/uploads/2016/11/iStock-177708665-5.jpg"

        }
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response_data = response.json()
        return Response(response_data)

    except requests.exceptions.RequestException as err:
        print("the payment didn't go through")
        return Response({"error": str(err)}, status=500)


class ApiRoute(viewsets.ModelViewSet):
    serializer_class = RouteSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['origin', 'destination']
    ordering_fields = ['departure_date', 'price']

    def get_serializer_class(self):
        if self.action == 'search':
            return SearchSerializer
        else:
            return super().get_serializer_class()

    def get_queryset(self):
        current_time = timezone.now()
        return Route.objects.filter(
            is_seat_remaining=True
        ).exclude(
            departure_date__lt=current_time.date()
        ).exclude(
            departure_date=current_time.date(),
            departure_time__lt=current_time.time().replace(microsecond=0)
        )

    @action(detail=False, methods=["POST"])
    def search(self, request):
        serializer = SearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        current_time = timezone.now()
        origin = serializer.validated_data["origin"]
        destination = serializer.validated_data["destination"]
        departure_date = serializer.validated_data["departure_date"]
        no_of_passengers = serializer.validated_data["no_of_passengers"]
        routes = Route.objects.filter(
            origin=origin, destination=destination, total_seats__gte=F('tickets_sold') + no_of_passengers

        ).exclude(
            departure_date__lt=current_time.date()
        ).exclude(
            departure_date=current_time.date(),
            departure_time__lt=current_time.time().replace(microsecond=0)
        )

        route_serializer = RouteSerializer(routes, many=True)
        return Response(route_serializer.data, status=status.HTTP_200_OK)


class ApiCities(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['cities']
    permission_classes = [IsAdminOrReadOnly]

    serializer_class = CitiesSerializer
    queryset = Cities.objects.all()


class ApiPending(viewsets.ModelViewSet):
    http_method_names = ["get", "patch", "post", "delete", "options", "head"]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['total_cost']

    @action(detail=True, methods=["POST"])
    def pay(self, request, pk):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            pending = self.get_object()
            current_time = timezone.now()
            qty = pending.no_of_passengers
            flight_id = pending.flight.id
            route = Route.objects.get(id=flight_id)
            available_seats = route.total_seats - route.tickets_sold

            if available_seats >= qty:
                if route.departure_date > current_time.date() or (route.departure_date==current_time.date() and route.departure_time > current_time.time().replace(microsecond=0)):
                    user = request.user
                    pending = self.get_object()
                    amount = pending.total_cost
                    email = request.user.email
                    pending_id = str(pending.id)
                    redirect_url = "http://127.0.0.1:8000/confirm"
                    return initiate_payment(amount, email, pending_id, user)
                else:
                    data = {
                        "msg": "flight has gone. try checking for current flights",
                    }
                    return Response(data, status=HTTP_400_BAD_REQUEST)
            else:
                data = {
                    "msg": f"There are not up to {qty} seats available; only {available_seats} seats left.",
                }
                return Response(data, status=HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["POST"])
    @transaction.atomic
    def confirm_payment(self, request):
        pending_id = request.GET.get("p_id")
        pending = Pending.objects.get(id=pending_id)
        user = request.user
        flight = Route.objects.get(id=pending.flight.id)
        flight.tickets_sold += pending.no_of_passengers
        flight.check_seat_availability()
        flight.save()
        instance = Booking(flight=pending.flight, no_of_passengers=pending.no_of_passengers,
                           total_cost=pending.total_cost, owner=user, )
        instance.save()
        Pending.objects.filter(id=pending_id).delete()

        serializer = BookingSerializer(instance)

        data = {
            "msg": "payment was successful",
            "data": serializer.data
        }
        return Response(data)

    permission_classes = [IsOwnerOrAdmin, IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Pending.objects.all()
        return Pending.objects.filter(owner=user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            qty = serializer.validated_data['no_of_passengers']
            flight_id = serializer.validated_data['flight'].id
            route = Route.objects.get(id=flight_id)
            available_seats = route.total_seats - route.tickets_sold

            if available_seats >= qty:
                instance = serializer.save(owner=request.user)
                self.perform_create(instance)
                headers = self.get_success_headers(serializer.data)
                return Response(serializer.data, status=HTTP_201_CREATED, headers=headers)
            else:
                data = {
                    "msg": f"There are not up to {qty} seats available; only {available_seats} seats left.",
                }
                return Response(data, status=HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return PendingSerializer
        if self.request.method == 'PATCH':
            return EditPendingSerializer
        return CreatePendingSerializer


class ApiBooking(viewsets.ModelViewSet):
    http_method_names = ["get", "patch", "delete", "options", "head"]
    permission_classes = [IsAdminOrReadOnly, IsAuthenticated]
    serializer_class = BookingSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    search_fields = ['flight_no']
    ordering_fields = ['placed_at', 'total_cost']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Booking.objects.all()
        return Booking.objects.filter(owner=user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
