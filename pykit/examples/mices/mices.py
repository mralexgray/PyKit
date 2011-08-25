from os import path
from decimal import InvalidOperation, Decimal

from pykit.driver.cocoa import PyKitApp, exceptions_to_stderr
from pykit.driver.cocoa_dom import js_function

import monocle.core
from monocle import _o, launch

from Quartz.CoreGraphics import *
from AppKit import *
#from AppKit import NSScreen
#speech reqs
#from AppKit import NSSpeechSynthesizer
import time
# font reqs
#from AppKit import NSFontManager

global width, height, originW, originH
width, height, originW, originH = 1, 1, 0, 0

def html_quote(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

class Cell(object):
    def __init__(self, x, y, sheet, jQ):
        self.x, self.y = x, y
        self.td = jQ('<td><span class="value"></span></td>')
        self.td.click(js_function(self.on_click))
        self.jQ = jQ
        self.value = ""
        self.sheet = sheet

    def on_click(self, this, event):
        # close any edit view
        if self.jQ(event.target).filter('input.edit-cell').length:
            return
        spreadsheet = self.td.closest('table.spreadsheet')
        self.jQ('input.edit-cell', spreadsheet).remove()

        # create our own edit box
        edit_input = self.jQ('<input class="edit-cell">')
        edit_input.val(unicode(self.value))
        edit_input.keydown(js_function(self.on_keydown))
        edit_input.prependTo(self.td).focus()

    def on_keydown(self, this, event):
        if event.keyCode not in (13, 27):
            return

        if event.keyCode == 13: # enter
            self.value = self.jQ(this).val()

        event.preventDefault()
        event.stopPropagation()
        self.jQ(this).remove()

    @property
    def computed_value(self):
        if self.is_formula:
            return eval(self._value[1:], {'S': self.sheet})
        else:
            try:
                return Decimal(self._value)
            except InvalidOperation:
                return self._value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        self._value = new_value
        self.is_formula = (new_value.startswith('='))
        self.update_ui()

    def update_ui(self):
        try:
            computed_value = self.computed_value
            display = html_quote(unicode(computed_value))
        except Exception, e:
            err = html_quote(repr(e))
            display = u'<span class="cell-error">%s</span>' % err
        else:
            if self.is_formula:
                display = u'<span class="computed-cell">%s</span>' % display
            elif isinstance(computed_value, Decimal):
                display = u'<span class="numeric-cell">%s</span>' % display
        self.td.children('span.value').html(display or u"\u00a0")

class Sheet(object):
    def __init__(self, jQ):
        self.jQ = jQ
        self.cells = {}

        self.table = jQ('<table class="spreadsheet">').appendTo(jQ("body"))
        self._width = 0
        self._height = 0

    def resize_width(self, new_width):
        assert new_width >= 0
        if new_width > self._width:
            for y in range(self._height):
                tr = self.jQ('tr:nth-child(%d)' % (y+1), self.table)
                for x in range(self._width, new_width):
                    self._new_cell(x, y).td.appendTo(tr)
        else:
            for y in range(self._height):
                tr = self.jQ('tr:nth-child(%d)' % (y+1), self.table)
                for x in reversed(range(new_width, self._width)):
                    print "del", x, y
                    del self.cells[x,y]
                    self.jQ('td:nth-child(%d)' % (x+1), tr).remove()
        self._width = new_width

    def resize_height(self, new_height):
        assert new_height >= 0
        if new_height > self._height:
            for y in range(self._height, new_height):
                tr = self.jQ('<tr>').appendTo(self.table)
                for x in range(self._width):
                    self._new_cell(x, y).td.appendTo(tr)
        else:
            for y in reversed(range(new_height, self._height)):
                for x in range(self._width):
                    print "del", x, y
                    del self.cells[x,y]
                self.jQ('tr:nth-child(%d)' % (y+1), self.table).remove()
        self._height = new_height

    def _new_cell(self, x, y):
        cell = self.cells[x,y] = Cell(x, y, self, self.jQ)
        return cell

    def __getitem__(self, key):
        return self.cells[key].computed_value

def path_in_module(name):
    return path.join(path.dirname(__file__), name)

def getScreenSize():
    global width, height, originW, originH
    width = NSScreen.mainScreen().frame().size.width
    height = NSScreen.mainScreen().frame().size.height
    return width, height
#silly speech rolecall
def voices():
    voices = NSSpeechSynthesizer.availableVoices()
    print voices
    voices = [x.split(".")[-1] for x in voices]
    return voices

def say(txt, voice='Samantha'):
    if voice in voices():
        voice = "com.apple.speech.synthesis.voice."+voice
    else:
        voice = NSSpeechSynthesizer.defaultVoice()
    speech = NSSpeechSynthesizer.alloc().initWithVoice_(voice)
    speech.startSpeakingString_(txt)

def sayTheVoices():
    speakers = voices()
    count = len(speakers) - 1
    while (count > 0):
       print 'The count is:', count
    try:
       say(speakers[count],speakers[count])
       time.sleep(1)
       count = count - 1
    except AttributeError:
       count = count - 1
#font experiment

def fonts():
    return NSFontManager.sharedFontManager().availableFonts()

    background(0.15, 0.1, 0.1)

    x, y, h = 0, 0, 0
    lineheight(1)
    fontsize(14)
    for f in fonts()[:250]:
        font(f)
        # Random pink, blue or white color
        fill(random(), random(0.5), 0.75)
        if random() > 0.8: fill(1)
        # Wrap text to the next line
        if x + textwidth(f) > WIDTH:
            x = 0
            y += h
            h = 0
        text(f, x, y)
        # Line height is equal to biggest font
        h = max(h, textheight(f))
        x += textwidth(f)

def setup_cocoa_app():

    app = AppKit.NSApplication.sharedApplication()
    app.setActivationPolicy_(0)
    app.setMainMenu_(AppKit.NSMenu.alloc().initWithTitle_("pykit"))
    url = AppKit.NSURL.alloc().initFileURLWithPath_(path_in_module("icon.png"))
    icon = AppKit.NSImage.alloc().initWithContentsOfURL_(url)
    app.setApplicationIconImage_(icon)
    app.activateIgnoringOtherApps_(True) # sort of rude

@exceptions_to_stderr
@_o
def main_o(app):
    global width, height, originW, originH
    setup_cocoa_app()
    getScreenSize()
    height = (height-18)
    wkw = yield app.create_window(size=(width, height), position=(0, 18))
    #wkw = yield app.create_window(size=(500, 300), position=(100, 20))
    window = wkw.window
    # thevoices = voices()
    # say("Poopie Vageen")
    # sayTheVoices()

    @js_function
    def console_log(this, *args):
        print ' '.join(repr(a) for a in args)
    window['console'] = window.eval('({})')
    window['console']['log'] = console_log

    with open(path_in_module('jquery-dev.js'), 'r') as jquery_src:
        window.eval(jquery_src.read())
    jQ = window.jQuery

    with open(path_in_module('mices.js'), 'r') as mices_js:
        jQ('head').append("<script>" + mices_js.read() + "</script>")
   
    with open(path_in_module('style.css'), 'r') as style_css:
        jQ('head').append("<style>" + style_css.read() + "</style>")

    buttons_div = jQ('<div>').appendTo(jQ('body'))
    def button(text, callback):
        @js_function
        def on_click(this, event):
            event.preventDefault()
            callback()
        button_a = jQ('<a href="#">').text(text).click(on_click)
        buttons_div.append('[', button_a, ']')

    sheet = Sheet(jQ)
    sheet.table.appendTo(jQ('body'))
    sheet.resize_width(4)
    sheet.resize_height(10)

    button('+ col', lambda: sheet.resize_width(sheet._width + 1))
    button('- col', lambda: sheet.resize_width(sheet._width - 1))
    button('+ row', lambda: sheet.resize_height(sheet._height + 1))
    button('- row', lambda: sheet.resize_height(sheet._height - 1))

    # window.fonts()
    wait_to_quit = monocle.core.Deferred()
    button('quit', lambda: wait_to_quit.callback(None))

    yield wait_to_quit
    app.terminate()

def main():
    app = PyKitApp()
    launch(main_o, app)
    app.run_loop()

if __name__ == '__main__':
    main()
