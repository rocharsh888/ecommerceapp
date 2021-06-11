from django.shortcuts import render,redirect
from .models import User,Contact,Product,Wishlist,Cart,Transaction
from django.conf import settings 
from django.core.mail import send_mail
import random
from .paytm import generate_checksum, verify_checksum
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
# Create your views here.


def validate_email_login(request):
	email=request.GET.get('email')
	data={
		'is_taken':User.objects.filter(email__iexact=email).exists()
	}
	return JsonResponse(data)


def initiate_payment(request):
    if request.method == "GET":
        return render(request, 'pay.html')
    try:
        
        amount = int(request.POST['amount'])
        user=User.objects.get(email=request.session['email'])
    except:
        return render(request, 'pay.html', context={'error': 'Wrong Accound Details or amount'})

    transaction = Transaction.objects.create(made_by=user,amount=amount)
    transaction.save()
    merchant_key = settings.PAYTM_SECRET_KEY

    params = (
        ('MID', settings.PAYTM_MERCHANT_ID),
        ('ORDER_ID', str(transaction.order_id)),
        ('CUST_ID', str("jigar93776@gmail.com")),
        ('TXN_AMOUNT', str(transaction.amount)),
        ('CHANNEL_ID', settings.PAYTM_CHANNEL_ID),
        ('WEBSITE', settings.PAYTM_WEBSITE),
        # ('EMAIL', request.user.email),
        # ('MOBILE_N0', '9911223388'),
        ('INDUSTRY_TYPE_ID', settings.PAYTM_INDUSTRY_TYPE_ID),
        ('CALLBACK_URL', 'http://localhost:8000/callback/'),
        # ('PAYMENT_MODE_ONLY', 'NO'),
    )

    paytm_params = dict(params)
    checksum = generate_checksum(paytm_params, merchant_key)

    user=User.objects.get(email=request.session['email'])
    carts=Cart.objects.filter(user=user,status="pending")
    for i in carts:
    	i.status="completed"
    	i.save()

    carts=Cart.objects.filter(user=user,status="pending")
    request.session['cart_count']=len(carts)

    transaction.checksum = checksum
    transaction.save()
    
    paytm_params['CHECKSUMHASH'] = checksum
    print('SENT: ', checksum)
    return render(request, 'redirect.html', context=paytm_params)


@csrf_exempt
def callback(request):
    if request.method == 'POST':
        received_data = dict(request.POST)
        paytm_params = {}
        paytm_checksum = received_data['CHECKSUMHASH'][0]
        for key, value in received_data.items():
            if key == 'CHECKSUMHASH':
                paytm_checksum = value[0]
            else:
                paytm_params[key] = str(value[0])
        # Verify checksum
        is_valid_checksum = verify_checksum(paytm_params, settings.PAYTM_SECRET_KEY, str(paytm_checksum))
        if is_valid_checksum:
            received_data['message'] = "Checksum Matched"
        else:
            received_data['message'] = "Checksum Mismatched"
            return render(request, 'callback.html', context=received_data)
        return render(request, 'callback.html', context=received_data)


def index(request):
	products=Product.objects.all()
	return render(request,'index.html',{'products':products})

def seller_index(request):
	return render(request,'seller_index.html')

def contact(request):
	if request.method=="POST":
		Contact.objects.create(
				name=request.POST['name'],
				email=request.POST['email'],
				subject=request.POST['subject'],
				remarks=request.POST['remarks']
			)
		msg="Contact Saved Successfully"
		contacts=Contact.objects.all().order_by('-id')[:5]
		return render(request,'contact.html',{'msg':msg,'contacts':contacts})
	else:
		contacts=Contact.objects.all().order_by('-id')[:5]
		return render(request,'contact.html',{'contacts':contacts})

def delivery(request):
	return render(request,'normal.html')

def special_offer(request):
	return render(request,'special_offer.html')

def register(request):
	if request.method=="POST":
		try:
			user=User.objects.get(email=request.POST['email'])
			msg="Email Already Registered"
			return render(request,'register.html',{'msg':msg})
		except:	
			User.objects.create(
					title=request.POST['title'],
					fname=request.POST['fname'],
					lname=request.POST['lname'],
					email=request.POST['email'],
					password=request.POST['password'],
					cpassword=request.POST['cpassword'],
					dob=request.POST['dob'],
					address=request.POST['address'],
					mobile=request.POST['mobile'],
					image=request.FILES['image'],
					usertype=request.POST['usertype']
				)
			email=request.POST['email']
			subject = 'OTP For Successfull Signup'
			otp=random.randint(1000,9999)
			message = 'Hello User, Your OTP For Successfull Signup Is : '+str(otp)
			email_from = settings.EMAIL_HOST_USER 
			recipient_list = [email,] 
			send_mail( subject, message, email_from, recipient_list)
			return render(request,'signup_otp.html',{'otp':otp,'email':email})
			
	else:
		return render(request,'register.html')

def legal_notice(request):
	return render(request,'legal_notice.html')

def tac(request):
	return render(request,'tac.html')

def faq(request):
	return render(request,'faq.html')

def product_summary(request):
	return render(request,'product_summary.html')

def login(request):
	if request.method=="POST":
		try:
			user=User.objects.get(email=request.POST['email'],password=request.POST['password'])
			if user.status=="inactive":
				msg1="Your Login Status Is Inactive."
				return render(request,'login.html',{'msg1':msg1})
			elif user.usertype=="user":
				wishlists=Wishlist.objects.filter(user=user)
				request.session['wishlist_count']=len(wishlists)
				carts=Cart.objects.filter(user=user)
				request.session['cart_count']=len(carts)
				request.session['fname']=user.fname
				request.session['email']=user.email
				request.session['image']=user.image.url
				return redirect('index')
			elif user.usertype=="seller":
				request.session['fname']=user.fname
				request.session['email']=user.email
				request.session['image']=user.image.url
				return render(request,'seller_index.html')
		except:
			msg="Email Or Password Is Incorrect Or Status Is Inactive"
			return render(request,'login.html',{'msg':msg,'email':request.POST['email']})
	else:
		return render(request,'login.html')

def logout(request):

	try:
		del request.session['fname']
		del request.session['email']
		del request.session['image']
		del request.session['wishlist_count']
		return render(request,'login.html')
	except:
		return render(request,'login.html')

def change_password(request):
	if request.method=="POST":
		user=User.objects.get(email=request.session['email'])
		if user.password==request.POST['old_password']:
			if request.POST['npassword']==request.POST['cnpassword']:
				user.password=request.POST['npassword']
				user.cpassword=request.POST['npassword']
				user.save()
				return redirect('logout')
			else:
				msg="New Password & Confirm New Password Does Not Matched"
				return render(request,'change_password.html',{'msg':msg})
		else:
			msg="Old Password Is Incorrect"
			return render(request,'change_password.html',{'msg':msg})

	else:
		return render(request,'change_password.html')

def seller_change_password(request):
	if request.method=="POST":
		user=User.objects.get(email=request.session['email'])
		if user.password==request.POST['old_password']:
			if request.POST['npassword']==request.POST['cnpassword']:
				user.password=request.POST['npassword']
				user.cpassword=request.POST['npassword']
				user.save()
				return redirect('logout')
			else:
				msg="New Password & Confirm New Password Does Not Matched"
				return render(request,'seller_change_password.html',{'msg':msg})
		else:
			msg="Old Password Is Incorrect"
			return render(request,'seller_change_password.html',{'msg':msg})

	else:
		return render(request,'seller_change_password.html')

def forgot_password(request):
	if request.method=="POST":
		email=request.POST['email']
		subject = 'OTP For Forgot Password'
		otp=random.randint(1000,9999)
		message = 'Hello User, Your OTP For Forgot Password Is : '+str(otp)
		email_from = settings.EMAIL_HOST_USER 
		recipient_list = [email,] 
		send_mail( subject, message, email_from, recipient_list)
		return render(request,'otp.html',{'otp':otp,'email':email})

	else:
		return render(request,'forgot_password.html')

def verify_otp(request):
	otp1=request.POST['otp1']
	otp2=request.POST['otp2']
	email=request.POST['email']
	
	if otp1==otp2:
		return render(request,'new_password.html',{'email':email})
	else:
		msg="Invalid OTP"
		return render(request,'otp.html',{'otp':otp1,'email':email,'msg':msg})

def new_password(request):
	np=request.POST['npassword']
	cnp=request.POST['cnpassword']
	email=request.POST['email']
	user=User.objects.get(email=email)
	if np==cnp:

		user.password=np
		user.cpassword=np
		user.save()
		return render(request,'login.html')
	else:
		msg="Password & Confirm Password Does Not Matched"
		return render(request,'new_password.html',{'email':email,'msg':msg})

def signup_verify_otp(request):
	otp1=request.POST['otp1']
	otp2=request.POST['otp2']
	email=request.POST['email']
	
	if otp1==otp2:
		user=User.objects.get(email=email)
		user.status="active"
		user.save()
		msg="Sign Up Successfull"
		return render(request,'login.html',{'msg':msg})
	else:
		msg="Invalid OTP"
		return render(request,'signup_otp.html',{'otp':otp1,'email':email,'msg':msg})

def activate_status(request):
	if request.method=="POST":
		email=request.POST['email']
		subject = 'OTP For Status Activation'
		otp=random.randint(1000,9999)
		message = 'Hello User, Your OTP For Activating Status Is : '+str(otp)
		email_from = settings.EMAIL_HOST_USER 
		recipient_list = [email,] 
		send_mail( subject, message, email_from, recipient_list)
		return render(request,'activate_staus_otp.html',{'otp':otp,'email':email})
	else:
		return render(request,'activate_status.html')

def activate_status_verify_otp(request):
	otp1=request.POST['otp1']
	otp2=request.POST['otp2']
	email=request.POST['email']
	
	if otp1==otp2:
		user=User.objects.get(email=email)
		user.status="active"
		user.save()
		return render(request,'login.html')
	else:
		msg="Invalid OTP"
		return render(request,'activate_staus_otp.html',{'otp':otp1,'email':email,'msg':msg})

def profile(request):
	user=User.objects.get(email=request.session['email'])
	if request.method=="POST":
		user.title=request.POST['title']
		user.fname=request.POST['fname']
		user.lname=request.POST['lname']
		user.email=request.POST['email']
		user.dob=request.POST['dob']
		user.address=request.POST['address']
		user.mobile=request.POST['mobile']
		try:
			user.image=request.FILES['image']
		except:
			pass
		user.save()
		msg="Profile Updated Successfully"
		request.session['image']=user.image.url
		return render(request,'profile.html',{'user':user,'msg':msg})
	else:
		return render(request,'profile.html',{'user':user})

def seller_profile(request):
	user=User.objects.get(email=request.session['email'])
	if request.method=="POST":
		user.title=request.POST['title']
		user.fname=request.POST['fname']
		user.lname=request.POST['lname']
		user.email=request.POST['email']
		user.dob=request.POST['dob']
		user.address=request.POST['address']
		user.mobile=request.POST['mobile']
		try:
			user.image=request.FILES['image']
		except:
			pass
		user.save()
		msg="Profile Updated Successfully"
		request.session['image']=user.image.url
		return render(request,'seller_profile.html',{'user':user,'msg':msg})
	else:
		return render(request,'seller_profile.html',{'user':user})

def seller_add_product(request):
	if request.method=="POST":
		seller=User.objects.get(email=request.session['email'])
		Product.objects.create(
				seller=seller,
				product_category=request.POST['product_category'],
				product_name=request.POST['product_name'],
				product_model=request.POST['product_model'],
				product_price=request.POST['product_price'],
				product_desc=request.POST['product_desc'],
				product_image=request.FILES['product_image']
			)
		msg="Product Added Successfully"
		return render(request,'seller_add_product.html',{'msg':msg})
	else:
		return render(request,'seller_add_product.html')

def seller_view_product(request):
	seller=User.objects.get(email=request.session['email'])
	products=Product.objects.filter(seller=seller)
	return render(request,'seller_view_product.html',{'products':products})

def seller_product_detail(request,pk):
	product=Product.objects.get(pk=pk)
	return render(request,'seller_product_detail.html',{'product':product})

def seller_edit_product(request,pk):
	product=Product.objects.get(pk=pk)
	if request.method=="POST":
		product.product_category=request.POST['product_category']
		product.product_name=request.POST['product_name']
		product.product_model=request.POST['product_model']
		product.product_price=request.POST['product_price']
		product.product_desc=request.POST['product_desc']
		try:
			product.product_image=request.FILES['product_image']
		except:
			pass
		product.save()
		return redirect('seller_view_product')
	else:
		return render(request,'seller_edit_product.html',{'product':product})

def seller_delete_product(request,pk):
	product=Product.objects.get(pk=pk)
	product.delete()
	return redirect('seller_view_product')

def user_product_detail(request,pk):
	wishlist_flag=False
	cart_flag=False
	product=Product.objects.get(pk=pk)
	user=User.objects.get(email=request.session['email'])
	try:
		wishlists=Wishlist.objects.get(user=user,product=product)
		wishlist_flag=True
	except:
		pass
	try:
		carts=Cart.objects.get(user=user,product=product)
		cart_flag=True
	except:
		pass
	return render(request,'user_product_detail.html',{'product':product,'wishlist_flag':wishlist_flag,'cart_flag':cart_flag})

def wishlist(request):
	user=User.objects.get(email=request.session['email'])
	wishlists=Wishlist.objects.filter(user=user)
	request.session['wishlist_count']=len(wishlists)
	return render(request,'wishlist.html',{'wishlists':wishlists})

def add_to_wishlist(request,pk):
	product=Product.objects.get(pk=pk)
	user=User.objects.get(email=request.session['email'])
	Wishlist.objects.create(user=user,product=product)
	return redirect('wishlist')

def remove_from_wishlist(request,pk):
	product=Product.objects.get(pk=pk)
	user=User.objects.get(email=request.session['email'])
	wishlist=Wishlist.objects.get(user=user,product=product)
	wishlist.delete()
	return redirect('wishlist')

def cart(request):
	net_price=0
	user=User.objects.get(email=request.session['email'])
	carts=Cart.objects.filter(user=user,status="pending")
	for i in carts:
		net_price=net_price+i.total_price
	request.session['cart_count']=len(carts)
	return render(request,'cart.html',{'carts':carts,'net_price':net_price})

def add_to_cart(request,pk):
	product=Product.objects.get(pk=pk)
	user=User.objects.get(email=request.session['email'])
	Cart.objects.create(user=user,product=product,price=product.product_price,qty=1,total_price=product.product_price)
	return redirect('cart')

def remove_from_cart(request,pk):
	product=Product.objects.get(pk=pk)
	user=User.objects.get(email=request.session['email'])
	cart=Cart.objects.get(user=user,product=product)
	cart.delete()
	return redirect('cart')

def change_qty(request):
	cart=Cart.objects.get(pk=request.POST['cid'])
	qty=int(request.POST['qty'])
	cart.qty=qty
	cart.total_price=cart.price*qty
	cart.save()
	return redirect('cart')	

def myorders(request):
	user=User.objects.get(email=request.session['email'])
	carts=Cart.objects.filter(user=user,status="completed")
	return render(request,'myorders.html',{'carts':carts})
