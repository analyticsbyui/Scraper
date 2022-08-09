from tkinter import *
from tkinter import ttk
import re
import json
class FeetToMeters:

    def __init__(self, root):

        self.root=root
        root.title("Scraper Configuration")

        mainframe = ttk.Frame(root, padding="3 3 12 12")
        mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        mainframe.columnconfigure(0, weight=1)
        mainframe.rowconfigure(0, weight=1)
        mainframe.columnconfigure(1, weight=1)
        mainframe.rowconfigure(1, weight=1)
        mainframe.rowconfigure(2, weight=1)
        mainframe.rowconfigure(3, weight=1)

        line=1

        self.crawl = IntVar()
        crawl=self.crawl
        crawl.set(1)
        crawl_check = ttk.Checkbutton(mainframe, text='Crawl', variable=crawl)#,onvalue=True, offvalue=False)
        crawl_check.grid(row=line,sticky=W)
        crawl.set(1)

        line+=1

        self.sitemap = IntVar()
        sitemap=self.sitemap
        sitemap.set(1)
        sitemap_check = ttk.Checkbutton(mainframe, text='Sitemap', variable=sitemap)#,onvalue=True, offvalue=False)
        sitemap_check.grid(row=line,sticky=W)
        sitemap.set(1)

        line+=1

        ttk.Label(mainframe, text="Max pages: ").grid(column=0, row=line,sticky=W)

        
        s = ttk.Style()
        s.configure('Danger.TFrame', background='red')#borderwidth=5,##,  relief='raised'
        self.color_frame = ttk.Frame(mainframe, padding="1")#padding="3 3 12 12",
        color_frame=self.color_frame
        color_frame.grid(column=1, row=line, sticky=(N, W, E, S))
        color_frame.columnconfigure(0, weight=1)
        #color_frame.columnconfigure(1, weight=1)
        color_frame.rowconfigure(0, weight=1)
        #color_frame.rowconfigure(1, weight=1)
        
        self.max = StringVar()
        self.max_entry = ttk.Entry(color_frame,  textvariable=self.max)#sticky=E
        self.max_entry.grid(sticky=(N, W, E, S),column=0,row=0)
        #self.meters = StringVar()

        #.grid(column=3, row=1, sticky=W)
        #ttk.Label(mainframe, text="is equivalent to").grid(column=1, row=2, sticky=E)
        #ttk.Label(mainframe, text="meters").grid(column=3, row=2, sticky=W)

        #ttk.Label(mainframe, textvariable=self.meters).grid(column=2, row=2, sticky=(W, E))\
        line+=1
        ttk.Button(mainframe, text="Save Config", command=self.save).grid(row=line)#, sticky=W

        

        for child in mainframe.winfo_children(): 
            child.grid_configure(padx=5, pady=5)

        #feet_entry.focus()
        root.bind("<Return>", self.save)
        
    def save(self, *args):
        exp = re.compile(r"\d+")
        if re.fullmatch(exp,self.max.get()):
            #save file
            #pass
            config={
                'crawl':self.crawl.get(),
                'sitemap':self.sitemap.get(),
                'max':int(self.max.get()),
                }
            with open('config.json','w') as f:
                f.write(json.dumps(config))
            self.root.destroy()
            #f=open('config.json','w')
            #f.write(json.dumps(config))
        else:
            print('b')
            self.color_frame.configure(style="Danger.TFrame")#{"background":"red"})#backgroundcolor="red")

root = Tk()
FeetToMeters(root)
root.mainloop()
