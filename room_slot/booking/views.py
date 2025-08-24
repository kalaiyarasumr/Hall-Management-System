from django.shortcuts import render, redirect
from .models import Contact, Rooms, Booking
from login.models import Customer
from django.contrib import messages
from django.http import HttpResponse
import datetime

# Index page
def index(request):
    return render(request, 'booking/index.html', {})

# Contact form
def contact(request):
    if request.method == "GET":
        return render(request, "contact/contact.html", {})
    else:
        username = request.POST['name']
        email = request.POST['email']
        message = request.POST['message']
        data = Contact(name=username, email=email, message=message)
        data.save()
        return render(request, "contact/contact.html", {'message': 'Thank you for contacting us.'})

# Book view (select room based on availability)
def book(request):
    if request.method == "POST":
        start_date = request.POST['start_date']
        end_date = request.POST['end_date']
        
        # Store dates in session
        request.session['start_date'] = start_date
        request.session['end_date'] = end_date
        
        # Convert to date objects
        start_date_obj = datetime.datetime.strptime(start_date, "%d/%b/%Y").date()
        end_date_obj = datetime.datetime.strptime(end_date, "%d/%b/%Y").date()
        no_of_days = (end_date_obj - start_date_obj).days
        
        # Check room availability based on the number of days
        available_rooms = Rooms.objects.filter(
            is_available=True, 
            no_of_days_advance__gte=no_of_days, 
            start_date__lte=start_date_obj
        )
        
        # Save number of days in session
        request.session['no_of_days'] = no_of_days
        return render(request, 'booking/book.html', {'data': available_rooms})
    else:
        return redirect('index')

# Book now (confirm room selection)
def book_now(request, id):
    if request.session.get("username", None) and request.session.get("type", None) == 'customer':
        no_of_days = request.session.get('no_of_days', 1)
        start_date = request.session.get('start_date')
        end_date = request.session.get('end_date')

        if not start_date or not end_date:
            return redirect('book')  # Redirect to booking step if dates are missing
        
        request.session['room_no'] = id
        room = Rooms.objects.get(room_no=id)
        bill = room.price * no_of_days
        request.session['bill'] = bill
        
        room_manager = room.manager.username
        return render(request, "booking/book-now.html", {
            "no_of_days": no_of_days,
            "room_no": id,
            "data": room,
            "bill": bill,
            "Customer": room_manager,
            "start": start_date,
            "end": end_date
        })
    else:
        # If the user is not logged in, redirect to login page
        return redirect('user_login')

# Confirm booking
def book_confirm(request):
    room_no = request.session['room_no']
    start_date = request.session['start_date']
    end_date = request.session['end_date']
    username = request.session['username']
    
    # Get customer and room information
    user = Customer.objects.get(username=username)
    room = Rooms.objects.get(room_no=room_no)
    amount = request.session['bill']
    
    # Convert string dates to date objects
    start_date_obj = datetime.datetime.strptime(start_date, "%d/%b/%Y").date()
    end_date_obj = datetime.datetime.strptime(end_date, "%d/%b/%Y").date()
    
    # Create new booking
    booking = Booking(room_no=room, start_day=start_date_obj, end_day=end_date_obj, amount=amount, user_id=user)
    booking.save()
    
    # Mark room as unavailable
    room.is_available = False
    room.save()
    
    # Clear session data related to the booking
    for key in ['start_date', 'end_date', 'bill', 'room_no']:
        if key in request.session:
            del request.session[key]
    
    # Inform the user
    messages.info(request, "Room has been successfully booked")
    return redirect('user_dashboard')

# Cancel room booking
def cancel_room(request, id):
    booking = Booking.objects.get(id=id)
    room = booking.room_no
    room.is_available = True
    room.save()
    booking.delete()
    return HttpResponse("Booking Cancelled Successfully")

# Delete room (only manager can delete)
def delete_room(request, id):
    room = Rooms.objects.get(id=id)
    manager = room.manager.username
    if manager == request.session['username']:
        room.delete()
        return HttpResponse("You have deleted the room successfully")
    else:
        return HttpResponse("Invalid Request")

# Date selection form view
def select_date_view(request):
    if request.method == "POST":
        start_date = request.POST.get('start_date')
        
        if start_date:
            request.session['start_date'] = start_date
            return redirect('book_now')  # Redirect to book_now view
        else:
            # Handle case where no date is provided
            return render(request, 'date_selection.html', {'error': 'Please select a start date.'})
    
    return render(request, 'date_selection.html')
