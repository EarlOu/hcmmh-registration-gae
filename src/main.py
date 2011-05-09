#!/usr/bin/env python
#coding=utf-8


from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app, login_required 
from google.appengine.api import memcache
from google.appengine.api import urlfetch
import BeautifulSoup
from django.utils import simplejson as json
import time
from datetime import date
from datetime import timedelta
import urllib2
import re
import httplib
import urllib
import cookielib
import Cookie

class MainPage(webapp.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('HsinChu Mackay Memorial Hospital Registration System:\nCCSP_HW2 B97901158')



def fetchHtml(url):
    r = urllib2.Request(url)
    r.add_header('User-Agent', 'Mozilla 5.0')
    page = urllib2.urlopen(r)
    return page

class deptList(db.Model):
    list = db.ListProperty(db.Key)
    
class deptInfo(db.Model):
    id = db.StringProperty()
    name = db.StringProperty()
    doctors = db.ListProperty(str)
    times = db.ListProperty(str)

class drList(db.Model):
    list = db.ListProperty(db.Key)
    
class drInfo(db.Model):
    id = db.StringProperty()
    name = db.StringProperty()
    depts = db.ListProperty(str)
    times = db.ListProperty(str)

def force_utf8(string):
    return unicode(string, 'utf-8')


def getInfo():
    albumUrl="http://reg07.mmh.org.tw/reg07/"
    page = fetchHtml(albumUrl)
    soup = BeautifulSoup.BeautifulSoup(page, fromEncoding="utf-8")
    ss = str(soup.findAll(attrs={"id":"tblDepts"})) 
    deptNameList =  re.findall('">.+ \(.+\)',ss)
    depts = []
    for i in deptNameList:
        tmp = deptInfo()
        tmp.name = unicode(str(i[2:-5]),'utf-8')
        tmp.id = force_utf8(i[-3:-1])
        depts.append(tmp)
    
    doctors = {}
    for dept in depts:
        albumUrl="http://reg07.mmh.org.tw/reg07/Dept.aspx?dept="+dept.id+"&Lang=C"
        page = fetchHtml(albumUrl)
        soup = BeautifulSoup.BeautifulSoup(page, fromEncoding="utf-8")
        roomlist = soup.body.find(attrs={"id":"tblSch"}).findAll("tr")[3:]
        today = date.today()
        for room in roomlist:
            doctorsstr = room.findAll("td")[1:]
            for i in range(len(doctorsstr)):         
                if doctorsstr[i].a:
                    doctorId = force_utf8(str(doctorsstr[i].a.contents[2]))
                    doctorName = force_utf8(str(doctorsstr[i].a.contents[0]))
                    if doctors.has_key(doctorId):
                        tmp = doctors[doctorId]
                    else:
                        tmp = drInfo() 
                    tmp.id = doctorId
                    tmp.name = doctorName
                    deptlist = set(tmp.depts)
                    deptlist.add(dept.id)
                    tmp.depts = list(deptlist)
                     
                    deltaday = i/3-today.weekday()
                    if deltaday <0:
                        deltaday+=7
                    day = today + timedelta(days=deltaday)
                    timestr="%(year)04d-%(month)02d-%(day)02d-" % {'year':day.year,'month':day.month,'day':day.day}
                    if(i%3 == 0):
                        timestr+='A'
                    elif(i%3 == 1):
                        timestr+='B'
                    else:
                        timestr+='C'
                    depttimeset = set(dept.times)
                    depttimeset.add(timestr)
                    dept.times = list(depttimeset)
                    drtimeset = set(tmp.times)
                    drtimeset.add(timestr)
                    tmp.times = list(drtimeset)
                    deptdrset = set(dept.doctors)
                    deptdrset.add(doctorId)
                    dept.doctors = list(deptdrset)
                    doctors[doctorId] = tmp

    deptListDB = deptList()
    doctorListDB = drList()
    deleteAll()
    for dept in depts:
        dept.put()
        deptListDB.list.append(dept.key())
    deptListDB.put()
    for doctor in doctors.itervalues():
        doctor.put()
        doctorListDB.list.append(doctor.key())
    doctorListDB.put()
        
def deleteAll():
    items = db.GqlQuery("SELECT * from deptList")
    for item in items:
        item.delete()
    items = db.GqlQuery("SELECT * from deptInfo")
    for item in items:
        item.delete()
    items = db.GqlQuery("SELECT * from drInfo")
    for item in items:
        item.delete()
    items = db.GqlQuery("SELECT * from drList")
    for item in items:
        item.delete()

        
class FetchInfo(webapp.RequestHandler):
    def get(self):
        getInfo()

class Dept(webapp.RequestHandler):
    def get(self):
        id = self.request.get('id','')
        list = db.GqlQuery("SELECT * from deptList").get()
        if list is None: 
            getInfo()
            list = db.GqlQuery("SELECT * from deptList").get()
        if id=='':
            output = []
            for item in list.list:
                dept = db.get(item)
                output.append({dept.id:dept.name})    
        else:
            dept  = db.GqlQuery("SELECT * from deptInfo where id = :1",id).get()
            output = []
            output.append({"id":dept.id})
            output.append({"name":dept.name})
            doctors = []
            for dr_id in dept.doctors:
                dr = db.GqlQuery("SELECT * from drInfo where id = :1",dr_id).get()
                doctors.append({dr.id:dr.name})
            output.append({"doctor":doctors})
            output.append({"time":dept.times})
        self.response.out.write(json.dumps(output, ensure_ascii=False))   
        
class Doctor(webapp.RequestHandler):
    def get(self):
        id = self.request.get('id','')
        list = db.GqlQuery("SELECT * from drList").get()
        if list is None: 
            getInfo()
            list = db.GqlQuery("SELECT * from drList").get()
        if id=='':
            output = []
            for item in list.list:
                dr = db.get(item)
                output.append({dr.id:dr.name})    
        else:
            dr  = db.GqlQuery("SELECT * from drInfo where id = :1",id).get()
            output = []
            output.append({"id":dr.id})
            output.append({"name":dr.name})
            depts = []
            for dept_id in dr.depts:
                dept = db.GqlQuery("SELECT * from deptInfo where id = :1",dept_id).get()
                depts.append({dept.id:dept.name})
            output.append({"doctor":depts})
            output.append({"time":dr.times})
        self.response.out.write(json.dumps(output, ensure_ascii=False))  


class Register(webapp.RequestHandler):
    def get(self):
        dr_id = self.request.get('doctor','')
        dept_id = self.request.get('dept','')
        time = self.request.get('time','')
        id = self.request.get('id','')
        birthday = self.request.get('birthday','')
        schdate = time[:4]+'/'+time[5:7]+'/'+time[8:10]
        dr_name = db.GqlQuery("SELECT * from drInfo where id = :1",dr_id).get()
    
        if time[11]=='A':
            schap = 1
        elif time[11]=='B':
            schap = 2
        else:
            schap = 3
            
        txtBirth = str(int(birthday[:4])-1911)+birthday[5:7]+birthday[8:10]
        params = {'dept':dept_id,'dr':dr_id,'drname':dr_name,'schdate':schdate,'schap':schap,'chgdr':'','Lang':'C'}
        paramsdata = urllib.urlencode(params)
        req = urllib2.Request("http://reg07.mmh.org.tw/reg07/Order.aspx?",paramsdata)
        response = urllib2.urlopen(req)
        regPage = response.read()
        key = re.findall('__VIEWSTATE.*',regPage)[0][20:-5]
        params2 = {'dept':dept_id,'dr':dr_id,'drname':dr_name,'schdate':schdate,'schap':schap,'chgdr':'','Lang':'C','Form1':'','txtID':id,'txtBirth':txtBirth,
                   '__VIEWSTATE':key,'btnInput':'\xe9\x80\x81\xe3\x80\x80\xe5\x87\xba','txtWebWord':''}
        paramsdata = urllib.urlencode(params2)
        req = urllib2.Request("http://reg07.mmh.org.tw/reg07/Order.aspx?",paramsdata)
        response = urllib2.urlopen(req)
        regPage = response.read()
        if re.findall('btnYes',regPage):
            key = re.findall('__VIEWSTATE.*',regPage)[0][20:-5]
            params2 = {'dept':dept_id,'dr':dr_id,'drname':dr_name,'schdate':schdate,'schap':schap,'chgdr':'','Lang':'C','Form1':'','txtID':id,'txtBirth':txtBirth,
                   '__VIEWSTATE':key,'btnYes':'\xe6\x98\xaf','txtWebWord':''}
            paramsdata = urllib.urlencode(params2)
            req = urllib2.Request("http://reg07.mmh.org.tw/reg07/Order.aspx?",paramsdata)
            response = urllib2.urlopen(req)
            regPage = response.read()
            
        
        number = re.findall("診號.*".decode('utf-8').encode('big5'),regPage)
        if number:
            number = number[0][6:9]
            output = {"status":"0","message":number}
        else:
            output = {"status":"1","message":"Error"}
            
        self.response.out.write(json.dumps(output, ensure_ascii=False))  
        
def loadPicture():
    cookie = Cookie.SimpleCookie()
    response = urlfetch.fetch(url="http://reg07.mmh.org.tw/reg07/Query.aspx?Lang=C")
    cookie.load(response.headers.get('Set-Cookie', ''))
    memcache.set("cookie",response.headers.get('Set-Cookie',''))
    
    
def getHeaders(cookie):
        headers = {
                 'User-Agent' : 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.2) Gecko/20090729 Firefox/3.5.2 (.NET CLR 3.5.30729)',
                 'Cookie' : makeCookieHeader(cookie)
                  }
        return headers

def makeCookieHeader(cookie):
        cookieHeader = ""
        for value in cookie.values():
            cookieHeader += "%s=%s; " % (value.key, value.value)
        return cookieHeader
    
class CancelRegister(webapp.RequestHandler):
    def get(self):      
        dr_id = self.request.get('doctor','')
        dept_id = self.request.get('dept','')
        time = self.request.get('time','')
        id = self.request.get('id','')
        birthday = self.request.get('birthday','')
        code = self.request.get('code','')
        if code=='':
            output = {"status":"2","message":[{"code":"code:http://hcmmh-registration.appspot.com/hcmmh/getPicture.jpg"}]}
            self.response.out.write(json.dumps(output, ensure_ascii=False)) 
            return
        
        
        cookie = memcache.get('cookie')
        
        if not cookie:
            loadPicture() 
            output = {"status":"1","message":"Check code timeout, please try again!"}
            self.response.out.write(json.dumps(output, ensure_ascii=False))             
            return
        cookie = Cookie.SimpleCookie()
        cookie.load(memcache.get('cookie'))
            
        
        txtBirth = str(int(birthday[:4])-1911)+birthday[5:7]+birthday[8:10]
        
        req = urllib2.Request("http://reg07.mmh.org.tw/reg07/Query.aspx?Lang=C")
        response = urllib2.urlopen(req)
        regPage = response.read()
        key = re.findall('__VIEWSTATE.*',regPage)[0][20:-5]
        params = {'txtID':id,'txtBirth':txtBirth,'txtCaptcha':code,
                   '__VIEWSTATE':key,'btnInput':'\xe9\x80\x81\xe3\x80\x80\xe5\x87\xba','txtWebWord':''}
        
        paramsdata = urllib.urlencode(params)       
        response = urlfetch.fetch(url="http://reg07.mmh.org.tw/reg07/Query.aspx?Lang=C",payload=paramsdata,
                                  method=urlfetch.POST,headers=getHeaders(cookie))
        
        
        if re.findall("Error",response.content):
            output = {"status":"1","message":"Wrong input data, please check again"}
            self.response.out.write(json.dumps(output, ensure_ascii=False))             
            return
        if re.findall("Time",response.content):
            loadPicture()
            output = {"status":"1","message":"Check code timeout, please try again!"}
            self.response.out.write(json.dumps(output, ensure_ascii=False))             
            return
        

        if re.findall('btnYes',response.content):
            key = re.findall('__VIEWSTATE.*',response.content)[0][20:-5]
            params = {'__VIEWSTATE':key,'btnYes':'\xe6\x98\xaf'}
            paramsdata = urllib.urlencode(params)
            response = urlfetch.fetch(url="http://reg07.mmh.org.tw/reg07/Query.aspx?Lang=C",payload=paramsdata,
                                      method = urlfetch.POST,headers=getHeaders(cookie))
            

        if time[11]=='A':
            schap = '1'
        elif time[11]=='B':
            schap = '2'
        else:
            schap = '3'
        
        schdate = "%04d" %(int(time[:4])-1911)
        schdate+= time[5:7]+time[8:10]
        key = re.findall('__VIEWSTATE.*',response.content)[0][20:-5]
        soup = BeautifulSoup.BeautifulSoup(response.content,fromEncoding="utf-8")
        value_Str = soup.find('tr',{'dr':dr_id,'dept':dept_id,'schdap':schap,'schdate':schdate})
        if value_Str is None:
            output = {"status":"1","message":"Wrong input data, please check again"}
            self.response.out.write(json.dumps(output, ensure_ascii=False))
            return
        value_Str = str(soup.find('tr',{'dr':dr_id,'dept':dept_id,'schdap':schap,'schdate':schdate}).td)
        value = re.findall('value="[0-9]+"',value_Str)[0][7:-1]
        params = {'__VIEWSTATE':key,'btnDel':'\xe9\x80\x81\xe3\x80\x80\xe5\x87\xba','cbx':value,'hdncbx':value}     
        paramsdata = urllib.urlencode(params)
        response = urlfetch.fetch(url="http://reg07.mmh.org.tw/reg07/Query.aspx?Lang=C",payload=paramsdata,
                                      method = urlfetch.POST,headers=getHeaders(cookie))
        
        output = {"status":"0"}
        self.response.out.write(json.dumps(output, ensure_ascii=False))

        
  
  
class GetPicture(webapp.RequestHandler):
    def get(self):
        cookie = Cookie.SimpleCookie()
        cookie.load(memcache.get('cookie'))
        response = urlfetch.fetch(url="http://reg07.mmh.org.tw/reg07/Captcha.aspx",
                          headers=getHeaders(cookie))
    
        img_data = response.content
        self.response.headers["Content-Type"] = "image/png"
        self.response.headers.add_header("Expires", "Thu, 01 Dec 1994 16:00:00 GMT")
        self.response.out.write(img_data)
        
        
class LoadPicture(webapp.RequestHandler):
    def get(self):        
        loadPicture()
        
                
def main():    
    app = webapp.WSGIApplication([             
        ('/hcmmh', MainPage),        
        ('/fetchInfo',FetchInfo),
        ('/hcmmh/dept',Dept),
        ('/hcmmh/doctor',Doctor),
        ('/hcmmh/register',Register),
        ('/hcmmh/cancel_register',CancelRegister),
        ('/hcmmh/getPicture.jpg',GetPicture),  
        ('/loadPicture',LoadPicture)                  
    ], debug=True)
    run_wsgi_app(app)

if __name__ == '__main__':
    main()