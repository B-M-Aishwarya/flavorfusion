from django.shortcuts import render, get_object_or_404, redirect
from myapp.models import Contact, Dish, Team, Category, Profile, Order
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
import razorpay
from decouple import config
from django.conf import settings

def index(request):
    context ={}
    cats = Category.objects.all().order_by('name')
    context['categories'] = cats
    # print()
    dishes = []
    for cat in cats:
        dishes.append({
            'cat_id':cat.id,
            'cat_name':cat.name,
            'cat_img':cat.image,
            'items':list(cat.dish_set.all().values())
        })
    context['menu'] = dishes
    return render(request,'index.html', context)

def contact_us(request):
    context={}
    if request.method=="POST":
        name = request.POST.get("name")
        mail = request.POST.get("email")
        sub = request.POST.get("subject")
        msg = request.POST.get("message")

        obj = Contact(name=name, email=mail, subject=sub, message=msg)
        obj.save()
        context['message']=(f"Dear {name}, Thanks for your time!!")
    return render(request,'contact.html',context)

def about(request):
    return render(request,'about.html')

def team_members(request):
    context={}
    members = Team.objects.all().order_by('name')
    context['team_members'] = members
    return render(request,'team.html', context)

def all_dishes(request):
    context={}
    dishes = Dish.objects.all()
    if "q" in request.GET:
        id = request.GET.get("q")
        dishes = Dish.objects.filter(category__id=id)
        context['dish_category'] = Category.objects.get(id=id).name 

    context['dishes'] = dishes
    return render(request,'all_dishes.html', context)

def register(request):
    context={}
    if request.method=="POST":
        #fetch data from html form
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('pass')
        contact = request.POST.get('number')
        check = User.objects.filter(username=email)
        if len(check)==0:
            #Save data to both tables
            usr = User.objects.create_user(email, email, password)
            usr.first_name = name
            usr.save()

            profile = Profile(user=usr, contact_number = contact)
            profile.save()
            context['status'] = f"User {name} Registered Successfully!"
        else:
            context['error'] = f"A User with this email already exists"

    return render(request,'register.html', context)

def check_user_exists(request):
    email = request.GET.get('usern')
    check = User.objects.filter(username=email)
    if len(check)==0:
        return JsonResponse({'status':0,'message':'Not Exist'})
    else:
        return JsonResponse({'status':1,'message':'A User with this email already Exists'})

def signin(request):
    context={}
    if request.method=="POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        check_user = authenticate(username=email, password=password)
        if check_user:
            login(request, check_user)
            if check_user.is_superuser or check_user.is_staff:
                return HttpResponseRedirect('/admin')
            return HttpResponseRedirect('/dashboard/')
        else:
            context.update({'message':'Invalid Login Details!','class':'alert-danger'})

    return render(request,'login.html', context)

def dashboard(request):
    context={}
    login_user = get_object_or_404(User, id = request.user.id)
    #fetch login user's details
    profile = Profile.objects.get(user__id=request.user.id)
    context['profile'] = profile

    #update profile
    if "update_profile" in request.POST:
        print("file=",request.FILES)
        name = request.POST.get('name')
        contact = request.POST.get('contact_number')
        add = request.POST.get('address')
       
        profile.user.first_name = name 
        profile.user.save()
        profile.contact_number = contact 
        profile.address = add 

        if "profile_pic" in request.FILES:
            pic = request.FILES['profile_pic']
            profile.profile_pic = pic
        profile.save()
        context['status'] = 'Profile updated successfully!'

        context.update({'profile_pic': profile})

    #Change Password 
    if "change_pass" in request.POST:
        c_password = request.POST.get('current_password')
        n_password = request.POST.get('new_password')

        check = login_user.check_password(c_password)
        if check==True:
            login_user.set_password(n_password)
            login_user.save()
            login(request, login_user)
            context['status'] = 'Password Updated Successfully!' 
        else:
            context['status'] = 'Current Password Incorrect!'  
    
    #My Orders
    orders = Order.objects.filter(customer__user__id=request.user.id).order_by('-id')
    context['orders']=orders    

    return render(request, 'dashboard.html', context)

def user_logout(request):
    logout(request)
    return HttpResponseRedirect('/')

def single_dish(request, id):
    context={}
    dish = get_object_or_404(Dish, id=id)

    if request.user.is_authenticated:
        cust = get_object_or_404(Profile, user__id = request.user.id)
        order = Order(customer=cust, item=dish)
        order.save()
        payer_id = f'PAYER-{order.id}'

    else:
        context.update({'alert': 'Please login'})
        return redirect('login')

       
    razorpay_client = razorpay.Client(auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))
       
    order_amount = int(dish.discounted_price * 100)
    order_currency = 'INR'
    order_receipt = 'order_'+ str(dish.id)
    order.payer_id = payer_id
    order.ordered_on = 'timezone.now()'
    order.save
    
    data = {
        'amount': order_amount,
        'currency': order_currency,
        'receipt': order_receipt,
        'payment_capture': '1'
    }
       
    razorpay_order = razorpay_client.order.create(data=data)

    order = Order.objects.create(
        customer=request.user.profile,
        item=dish,
        status=False,
        payer_id=payer_id,
        razorpay_order_id=razorpay_order['id']
    )

    razor_key = config('RAZOR_KEY_ID')
    razor_secret = config('RAZOR_KEY_SECRET')
    context = {
        'razor_key': razor_key,
        'razor_secret': razor_secret
    }

    context.update({'dish': dish, 'order_id': razorpay_order['id'], 'razorpay_key': settings.RAZOR_KEY_ID, 'order': order, 'payer_id': order.payer_id})

    return render(request, 'dish.html', context)

def payment_done(request):
   
    pid = request.GET.get('PayerID')
    order_id = request.session.get('order_id')
    order_obj = Order.objects.get(id=order_id)
    order_obj.status=True 
    order_obj.payer_id = pid
    order_obj.save()

    return render(request, 'payment_successful.html')

def payment_cancel(request):
    
    return render(request, 'payment_failed.html')
