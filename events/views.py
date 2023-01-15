from django.shortcuts import render, redirect
import calendar
from calendar import HTMLCalendar
from datetime import datetime
from django.http import HttpResponseRedirect, HttpResponse
from .models import Event, Venue
from django.contrib.auth.models import User
from .forms import VenueForm, EventForm, EventFormAdmin
import csv
from django.contrib.auth.decorators import login_required
from django.contrib import messages
#for pdf
from django.http import FileResponse
import io
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter

#Import pagination tools
from django.core.paginator import Paginator

# Create your views here.

def show_event(request, event_id):
	event = Event.objects.get(pk = event_id)
	return render(request, 'events/show_event.html', {'event' : event, })
def venue_events(request, venue_id):
	#Get the venue
	venue = Venue.objects.get(id=venue_id)
	#Get evens from that venue
	events = venue.event_set.all()
	if events:
		return render(request, 'events/venue_events.html', {'events' : events, })
	else:
		messages.success(request, ('This venue has no evens at this time...'))
		return redirect('admin_approval')
#Create admin event approval page
def admin_approval(request):
	#Get the venes
	venue_list = Venue.objects.all()
	#Get counts
	event_count = Event.objects.all().count()
	venue_count = Venue.objects.all().count()
	user_count = User.objects.all().count()

	event_list = Event.objects.all().order_by('-event_date')
	if request.user.is_superuser:
		if request.method == "POST":
			id_list = request.POST.getlist('boxes')
			#uncheck all events
			event_list.update(approved=False)
			#update a db
			for x in id_list:
				Event.objects.filter(pk= int(x)).update(approved=True)
			messages.success(request, ('Aproval status updated'))
			return redirect('list-events')
		else:
			return render(request, 'events/admin_approval.html', {
				'event_list' : event_list,
				'event_count' : event_count,
				'venue_count' : venue_count,
				'user_count' : user_count,
				'venue_list' : venue_list, })
	else:
		messages.success(request, ('You are not authorised to view this page!'))
		return redirect('home')
	return render(request, 'events/admin_approval.html', {})

#Create My Events Page

def my_events(request):
	if request.user.is_authenticated:
		me = request.user.id
		events = Event.objects.filter(attendees=me)
		return render(request, 'events/my_events.html',
			{
			'events' : events,
			})
	else:
		messages.success(request, ('You are not authorised to view this page! Please login.'))
		return redirect('login')

#Generate a pdf file venue list
def venue_pdf(request):
	#Ceate a Bitestream buffer
	buf = io.BytesIO()
	#Create a canvas
	c = canvas.Canvas(buf, pagesize=letter, bottomup = 0)
	#Create a text object
	textob = c.beginText()
	textob.setTextOrigin(inch, inch)
	textob.setFont('Helvetica', 14)
	#Add lines of text

	#lines = ['This is line 1',
	#		'This is line 2',
	#		'This is line 3']

	#Designate the model
	venues = Venue.objects.all()

	lines = []
	for venue in venues:
		lines.append(venue.name)
		lines.append(venue.address)
		lines.append(venue.zip_code)
		lines.append(venue.phone)
		lines.append(venue.web)
		lines.append(venue.email_address)
		lines.append(' ')

	for line in lines:
		textob.textLine(line)
	c.drawText(textob)
	c.showPage()
	c.save()
	buf.seek(0)

	return FileResponse(buf, as_attachment = True, filename = 'venue.pdf')




# Generating csv venue list file
def venue_csv(request):
	response = HttpResponse(content_type='text/csv')
	response['Content-Disposition'] = 'attachment; filename=venues.csv'
	
	# create a csv wrier
	writer = csv.writer(response)

	#Designate the model
	venues = Venue.objects.all()
	#add column headings to a csv file
	writer.writerow(['Venue Name', 'Address', 'Zip Code', 'Phone', 'Web Address', 'Email'])

	for venue in venues:
		writer.writerow([
			venue,
			venue.address,
			venue.zip_code,
			venue.phone,
			venue.web,
			venue.email_address])
	return response

# Generating txt venue list file
def venue_text(request):
	response = HttpResponse(content_type='text/plain')
	response['Content-Disposition'] = 'attachment; filename=venues.txt'
	#Designate the model
	venues = Venue.objects.all()
	#Loop through and output
	lines = []
	for venue in venues:
		lines.append(f'''
			{venue}\n
			{venue.address}\n
			{venue.zip_code}\n
			{venue.phone}\n
			{venue.web}\n
			{venue.email_address}\n\n\n''')
	#lines = ['This is line 1\n',
	#		'This is line 2\n',
	#		'This is line 3\n']

	#Write to txt file
	response.writelines(lines)
	return response



#Deleting venue
def delete_venue(request, venue_id):
	venue = Venue.objects.get(pk = venue_id)
	venue.delete()
	messages.success(request, ('Venue Deleted!'))
	return redirect('list-venues')

#Deleting an event
def delete_evet(request, event_id):
	event = Event.objects.get(pk = event_id)
	if request.user == event.manager: 
		event.delete()
		messages.success(request, ('Event Deleted!'))
		return redirect('list-events')
	else:
		messages.success(request, ('You are not authorised to delete this event!'))
		return redirect('list-events')

@login_required(login_url='login')
def add_event(request):
	submitted = False
	if request.method == "POST":
		if request.user.is_superuser:
			form = EventFormAdmin(request.POST)
			if form.is_valid():
				form.save()
				return HttpResponseRedirect('/add_event?submitted=True')
		else:
			form = EventForm(request.POST)
			if form.is_valid():
				event = form.save(commit=False)
				event.manager = request.user #logged in user
				event.save()
				return HttpResponseRedirect('/add_event?submitted=True')
	else:
		#Returning to the page without submitting
		if request.user.is_superuser:
			form = EventFormAdmin
		else:
			form = EventForm
		if 'submitted' in request.GET:
			submitted = True
	return render(request, 'events/add_event.html',
			{'form': form, 'submitted' : submitted})


	
def update_event(request, event_id):
	event = Event.objects.get(pk = event_id)
	if request.user.is_superuser:
		form = EventFormAdmin(request.POST or None, instance = event)
	else:
		form = EventForm(request.POST or None, instance = event)
	if form.is_valid():
		form.save()
		return redirect('list-events')
	event_list = Event.objects.all()
	return render(request, 'events/update_event.html', {'event' : event, 'form': form})


def update_venue(request, venue_id):
	venue = Venue.objects.get(pk = venue_id)
	form = VenueForm(request.POST or None, request.FILES or None, instance = venue)
	if form.is_valid():
		form.save()
		return redirect('list-venues')
	venue_list = Venue.objects.all()
	return render(request, 'events/update_venue.html', {'venue' : venue, 'form': form})

def search_venues(request):
	if request.method == 'POST':
		searched = request.POST['searched']
		venues = Venue.objects.filter(name__contains = searched)
		return render(request, 'events/search_venues.html', {'searched': searched, 'venues': venues })
	else:
		return render(request, 'events/search_venues.html' )

def search_events(request):
	if request.method == 'POST':
		searched = request.POST['searched']
		events = Event.objects.filter(description__contains = searched)
		return render(request, 'events/search_events.html', {'searched': searched, 'events': events })
	else:
		return render(request, 'events/search_events.html' )

def show_venue(request, venue_id ):
	venue = Venue.objects.get(pk = venue_id)
	venue_list = Venue.objects.all()
	venue_owner = User.objects.get(pk = venue.owner)
	events = venue.event_set.all()
	return render(request, 'events/show_venue.html', {'venue' : venue,
		'venue_owner' : venue_owner, 'events': events })

def list_venues(request):
	#venue_list = Venue.objects.all().order_by('?')
	#venue_list = Venue.objects.all()
	#Set up pagination (first arg is a call to db,
	#second - number of ecord per page)
	p=Paginator(Venue.objects.all(), 2)
	page = request.GET.get('page')
	venues = p.get_page(page)
	nums = "a" * venues.paginator.num_pages
	return render(request, 'events/venues.html', 
		{#'venue_list' : venue_list, 
		'venues' : venues,
		'nums' : nums })

@login_required(login_url='login')
def add_venue(request):
	submitted = False
	if request.method == "POST":
		form = VenueForm(request.POST, request.FILES)
		if form.is_valid():
			venue = form.save(commit=False)
			venue.owner = request.user.id #logged in user
			venue.save()
			#form.save()
			return HttpResponseRedirect('/add_venue?submitted=True')
	else:
		form = VenueForm
		if 'submitted' in request.GET:
			submitted = True
	return render(request, 'events/add_venue.html',
			{'form': form, 'submitted' : submitted})

def all_events(request):
	event_list = Event.objects.all().order_by('-event_date')
	return render(request, 'events/event_list.html', { "event_list" : event_list})


def home(request, year = datetime.now().year, month= datetime.now().strftime('%B')):
	name = "Denis"
	month = month.title()
	# convert month from name to number
	month_number = list(calendar.month_name).index(month)
	month_number = int(month_number)

	# create calendar
	cal = HTMLCalendar().formatmonth(
		year,
		month_number)
	# get current year

	now = datetime.now()
	current_year = now.year

	#Query the Events model for dates
	event_list = Event.objects.filter(

		event_date__year = year,
		event_date__month = month_number,
		)
	

	#get current time
	time = now.strftime('%I:%M:%S %p')
	return render(request, 'events/home.html', { "name": name,
	"year" : year,
	"month" : month,
	"month_number" : month_number,
	"cal" : cal,
	"current_year" : current_year,
	"time" : time,
	"event_list" : event_list,
	})