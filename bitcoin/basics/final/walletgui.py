import kivy
kivy.require('1.11.1') # replace with your current kivy version !

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.config import Config
from kivy.uix.image import AsyncImage
from kivy.properties import StringProperty,BooleanProperty
from kivy.uix.screenmanager import ScreenManager, Screen
Config.set('graphics','width',300)
Config.set('graphics','height',600)



class MainScreen(Screen):
    btc_balance=1234567
    usd_balance=100000000
    btc_balance_text = StringProperty(str(btc_balance) + " BTC")
    usd_balance_text = StringProperty("~100 billion USD")
    font_size = "20sp"
    
    def update_balance(self):
        self.btc_balance_text =  str(self.btc_balance*1.5) + " BTC"
        self.usd_balance_text = "~150 billion USD"
        
        
class SendScreen(Screen):
  
    def confirm_popup(self):
        self.show = ConfirmSendPopup()
        self.popupWindow = Popup(title="Confirm Transaction", content=self.show, size_hint=(None,None), size=(280,280), 
                            #auto_dismiss=False
                           )
        self.popupWindow.open()
        #self.show.YES.bind(on_press=self.send_tx)
        self.show.YES.bind(on_release=self.go_back)
        self.show.CANCEL.bind(on_release=self.popupWindow.dismiss)
        
    
    def send_tx(self,screen):
        "the button is the Button object"
        print(screen.show.YES.text)
        print("SENDING TX")
        
    def go_back(self,button):
        self.send_tx(self)
        #app = WindowManager()
        #Main = MainScreen(name="Main")
        #app.add_widget(Main)
        #app.switch_to(Main,direction="right")
        self.popupWindow.dismiss()
        print("just did go bakc")
        
        
        
class ConfirmSendPopup(FloatLayout):
    def __init__(self):
        super().__init__()
        #self.orientation="vertical")
        message = Label(text="Are you sure you want \nto send xx.xxx BTC to adress\n abc666lkp1233?",
                       halign="center",size_hint= (0.6,0.3), 
                        pos_hint={"x":0.2, "top":1}
                       )

        self.YES = Button(text="YES",
                     pos_hint= {"x":0, "y":0.35}, 
                     size_hint= (1,0.17),
                          background_color=[0.5,1,0.75,1]
                      )
        self.CANCEL = Button(text="CANCEL",
                     pos_hint= {"x":0, "y":-0.01}, 
                     size_hint= (1,0.3),
                             background_color=[1,0.3,0.3,1]
                      )
        self.add_widget(message)
        self.add_widget(self.YES)
        self.add_widget(self.CANCEL)
        
        
class QRcodePopup(FloatLayout):
    def __init__(self):
        super().__init__()
        #self.orientation="vertical")
        qrcode = AsyncImage(source='https://storage.googleapis.com/support-forums-api/attachment/thread-13090132-506909745012483037.png',
                            size_hint= (0.8, 0.8),size=(210,210),
                            pos_hint= {'center_x':.5, 'center_y': 0.65} )
        
        address = Label(text="sdljfa4o8nj3o40nkqjv0dsddslg8",
                       halign="center",size_hint= (0.6,0.25), 
                        pos_hint={"center_x":0.5, "center_y":0.23}
                       )
        
        self.OK = Button(text="OK",
                     pos_hint= {"x":0, "y":0.01}, 
                     size_hint= (1,0.15),
                             background_color=[0.6,0.9,1,1]
                      )
        self.add_widget(qrcode)
        self.add_widget(address)
        self.add_widget(self.OK)
    

class ReceiveScreen(Screen):
    label_font_size = "15sp"
    def qr_popup(self):
        self.show = QRcodePopup()
        self.popupWindow = Popup(title="Address QR Code", content=self.show, size_hint=(None,None), size=(280,380))
        self.popupWindow.open()
        #self.show.YES.bind(on_press=self.send_tx)
        self.show.OK.bind(on_release=self.popupWindow.dismiss)
    
    def activate_spinner(self):
        new_addr = True
    
    
        
        
class WindowManager(ScreenManager):
    pass




kv = Builder.load_file("walletgui.kv")


class walletguiApp(App):
    title = "Wallet"
    def build(self):
        return kv


if __name__ == '__main__':
    walletguiApp().run()
    
    