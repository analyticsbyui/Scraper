from tkinter import *
from tkinter import ttk
import re
import json
class ConfigScraper:
    def __setitem__(self, key, value):
        setattr(self, key, value)
    def __getitem__(self, key):
        return getattr(self, key)
    def __init__(self, root):

        self.root=root
        root.title("Scraper Configuration")

        
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        settings_frame = ttk.Labelframe(root, text='Settings')
        settings_frame.grid(column=0, row=0, sticky=(N, W, E, S))

        columns_frame = ttk.Labelframe(root, text='Columns')
        columns_frame.grid(column=1, row=0, sticky=(N, W, E, S))

        mainframe = ttk.Frame(settings_frame, padding="3 3 12 12")
        mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
        
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
        crawl_check = ttk.Checkbutton(mainframe, text='Crawl', variable=crawl)
        crawl_check.grid(row=line,sticky=W)
        crawl.set(1)

        line+=1

        self.sitemap = IntVar()
        sitemap=self.sitemap
        sitemap.set(1)
        sitemap_check = ttk.Checkbutton(mainframe, text='Sitemap', variable=sitemap)
        sitemap_check.grid(row=line,sticky=W)
        sitemap.set(1)

        line+=1

        ttk.Label(mainframe, text="Max pages: ").grid(column=0, row=line,sticky=W)

        
        s = ttk.Style()
        s.configure('Danger.TFrame', background='red')
        self.color_frame = ttk.Frame(mainframe, padding="1")
        color_frame=self.color_frame
        color_frame.grid(column=1, row=line, sticky=(W, E))
        color_frame.columnconfigure(0, weight=1)
        color_frame.rowconfigure(0, weight=1)
        
        self.max = StringVar()
        self.max_entry = ttk.Entry(color_frame,  textvariable=self.max)
        self.max_entry.grid(sticky=(W, E),column=0,row=0)
        
        line+=1
        ttk.Button(mainframe, text="Save Config", command=self.save).grid(row=line, sticky=(S))


        mainframe = ttk.Frame(columns_frame, padding="3 3 12 12")
        mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
        
        mainframe.columnconfigure(0, weight=1)
        mainframe.rowconfigure(0, weight=1)
        mainframe.columnconfigure(1, weight=1)
        mainframe.rowconfigure(1, weight=1)
        mainframe.rowconfigure(2, weight=1)
        mainframe.rowconfigure(3, weight=1)

        line=0

        self.columns={
            'url':{'disabled':True,'state':True},
            'aliases':{'disabled':False,'state':False},
            'errorCode':{'disabled':False,'state':False},
            'tracking_ids':{'disabled':False,'state':False},
            'loadTime':{'disabled':False,'state':False},
            'dateCrawled':{'disabled':False,'state':False},
            'cookies':{'disabled':False,'state':False},
            'links':{'disabled':False,'state':False}
        }

        for column in self.columns.keys():
            self[column]=IntVar()
            self[column].set(self.columns[column]['state'])
            cb=ttk.Checkbutton(mainframe, text=column, variable=self[column])
            cb.grid(row=line,sticky=W)
            if self.columns[column]['disabled']:
                cb.config(state='disabled')
            line+=1

        #ttk.Label(mainframe, text="Terms: ").grid(column=0, row=line,sticky=W)
        
        
        self.color_frame_f = ttk.Frame(mainframe, padding="1")
        color_frame_f=self.color_frame_f
        color_frame_f.grid(column=1, row=line, sticky=(W, E))
        color_frame_f.columnconfigure(0, weight=1)
        color_frame_f.rowconfigure(0, weight=1)
        
        self.terms = StringVar()
        self.terms_entry = ttk.Entry(color_frame_f,  textvariable=self.terms, state='disabled')
        self.terms_entry['state']='disabled'
        self.terms_entry.grid(sticky=(W, E),column=0,row=0)

        self.terms_s=IntVar()
        self.terms_s.set(0)
        cb=ttk.Checkbutton(mainframe, text="Terms: ", variable=self.terms_s, command=self.change_terms_state)
        cb.grid(row=line,column=0,sticky=W)
        

        for child in mainframe.winfo_children(): 
            child.grid_configure(padx=5, pady=5)

        #feet_entry.focus()
        root.bind("<Return>", self.save)
    def change_terms_state(self):
        self.alternate_entry(self.terms_entry)
        self.color_frame_f.configure(style="")
    def alternate_entry(self,entry,state=None):
        if state==None:
            #print(entry['state'])
            #print(entry.cget("state"))
            #if(entry["state"]=='disabled'):
            es=entry.state()
            if(len(es)>0 and es[0]=='disabled'):
                entry.config(state='enabled')
            else:
                entry.config(state='disabled')
        elif state:
            entry.config(state='enabled')
        else:
            entry.config(state='disabled')
    def save(self, *args):
        exp = re.compile(r"\d+")
        ready=True
        if re.fullmatch(exp,self.max.get()):
            ready=ready and True
            self.color_frame.configure(style="")
        else:
            ready=False
            self.color_frame.configure(style="Danger.TFrame")
        exp = re.compile(r"[^ ]+.*")
        es=self.terms_entry.state()
        if (len(es)>0 and es[0]=='disabled') or re.fullmatch(exp,self.terms.get()):
            ready=ready and True
            self.color_frame_f.configure(style="")
        else:
            ready=False
            self.color_frame_f.configure(style="Danger.TFrame")
        if ready:
            terms=self.terms.get() if len(es)==0 else ""
            columns_values={}
            columns_values.update([[column, self[column].get()] for column in self.columns])
            columns_values.update([['terms',1 if len(es)==0 else 0]])
            config={
                'crawl':self.crawl.get(),
                'sitemap':self.sitemap.get(),
                'terms':terms,
                'columns':columns_values,
                'max':int(self.max.get()),
                }
            with open('config.json','w') as f:
                f.write(json.dumps(config))
            self.root.destroy()

root = Tk()
ConfigScraper(root)
root.mainloop()
