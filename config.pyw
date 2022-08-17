from tkinter import *
import tkinter.filedialog as filedialog
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
        mainframe.columnconfigure(2, weight=1)
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

        self.catalog = IntVar()
        catalog=self.catalog
        catalog.set(1)
        catalog_check = ttk.Checkbutton(mainframe, text='Catalog', variable=catalog)
        catalog_check.grid(row=line,sticky=W)
        catalog.set(0)

        line+=1

        self.link = IntVar()
        link=self.link
        link.set(1)
        link_check = ttk.Checkbutton(mainframe, text='Links:', variable=link, command=self.change_link_file_state)
        link_check.grid(column=0,row=line,sticky=W)
        link.set(0)

        self.link_file = StringVar()
        self.link_file_entry = ttk.Entry(mainframe,  textvariable=self.link_file, state='disabled')
        self.link_file_entry['state']='disabled'
        self.link_file_entry.grid(sticky=(W, E),column=1,row=line)

        self.button = ttk.Button(mainframe, text='File', command=self.open_file)
        self.button.grid(sticky=(W, E),column=2,row=line)
        self.button.state(['disabled'])

        line+=1

        self.blacklist = IntVar()
        blacklist=self.blacklist
        blacklist.set(1)
        blacklist_check = ttk.Checkbutton(mainframe, text='Blacklists: ', variable=blacklist, command=self.change_blacklist_file_state)
        blacklist_check.grid(column=0,row=line,sticky=W)
        blacklist.set(0)

        self.blacklist_file = StringVar()
        self.blacklist_file_entry = ttk.Entry(mainframe,  textvariable=self.blacklist_file, state='disabled')
        self.blacklist_file_entry['state']='disabled'
        self.blacklist_file_entry.grid(sticky=(W, E),column=1,row=line)

        self.button_blacklist = ttk.Button(mainframe, text='File', command=self.open_file_blacklist)
        self.button_blacklist.grid(sticky=(W, E),column=2,row=line)
        self.button_blacklist.state(['disabled'])

        line+=1

        subentryframe = ttk.Frame(mainframe)
        subentryframe.grid(column=1, row=line, sticky=(N, W, E, S))
        
        self.blacklisted = IntVar()
        blacklisted=self.blacklisted
        blacklisted.set(1)
        self.blacklisted_check = ttk.Checkbutton(subentryframe, text='Output: ', variable=blacklisted, command=self.change_blacklisted_file_state)
        self.blacklisted_check.grid(column=0,row=line,sticky=W)
        blacklisted.set(0)

        self.blacklisted_file = StringVar()
        self.blacklisted_file_entry = ttk.Entry(subentryframe,  textvariable=self.blacklisted_file, state='disabled')
        self.blacklisted_file_entry['state']='disabled'
        self.blacklisted_file_entry.grid(sticky=(W, E),column=1,row=line)

        self.button_blacklisted = ttk.Button(mainframe, text='File', command=self.open_file_blacklisted)
        self.button_blacklisted.grid(sticky=(W, E),column=2,row=line)
        self.button_blacklisted.state(['disabled'])
        self.blacklisted_check.state(['disabled'])

        line+=1

        self.terms_dfile=IntVar()
        self.terms_dfile.set(0)
        self.terms_d = ttk.Checkbutton(mainframe, text='Terms file:', variable=self.terms_dfile, command=self.change_terms_file_state)
        self.terms_d.grid(column=0,row=line,sticky=W)
        self.terms_d['state']='disabled'

        self.terms_file = StringVar()
        self.terms_file_entry = ttk.Entry(mainframe,  textvariable=self.terms_file, state='disabled')
        self.terms_file_entry['state']='disabled'
        self.terms_file_entry.grid(sticky=(W, E),column=1,row=line)

        self.button_terms = ttk.Button(mainframe, text='File', command=self.open_file_terms)
        self.button_terms.grid(sticky=(W, E),column=2,row=line)
        self.button_terms.state(['disabled'])

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

        self.cb=ttk.Checkbutton(mainframe, text="Terms: ", variable=self.terms_s, command=self.change_terms_state)
        self.cb.grid(row=line,column=0,sticky=W)
        self.cb.state(['!disabled'])


        for child in mainframe.winfo_children(): 
            child.grid_configure(padx=5, pady=5)

        #feet_entry.focus()
        root.bind("<Return>", self.save)
    def change_terms_state(self):
        if(self.cb.instate(['selected'])):
            self.terms_entry.state(['!disabled'])
            self.terms_d.state(['!disabled'])
        else:
            self.terms_entry.state(['disabled'])
            self.color_frame_f.configure(style="")
            self.terms_d.state(['disabled'])
            self.terms_file_entry.state(['disabled'])
            self.button_terms.state(['disabled'])
            self.terms_dfile.set(0)
            
        
    def change_link_file_state(self):
        self.alternate_entry(self.link_file_entry)
        if self.button.instate(['disabled']):
            self.button.state(['!disabled'])
        else:
            self.button.state(['disabled'])
    def change_blacklist_file_state(self):
        self.alternate_entry(self.blacklist_file_entry)
        if self.button_blacklist.instate(['disabled']):
            self.button_blacklist.state(['!disabled'])
            self.blacklisted_check.state(['!disabled'])
        else:
            self.button_blacklist.state(['disabled'])
            self.button_blacklisted.state(['disabled'])
            self.blacklisted_check.state(['disabled'])
            self.blacklisted_file_entry.state(['disabled'])
            self.blacklisted.set(0)
    def change_blacklisted_file_state(self):
        self.alternate_entry(self.blacklisted_file_entry)
        if self.button_blacklisted.instate(['disabled']):
            self.button_blacklisted.state(['!disabled'])
        else:
            self.button_blacklisted.state(['disabled'])
    def change_terms_file_state(self):
        if(not self.terms_d.instate(['selected'])):
            self.terms_file_entry.state(['disabled'])
            self.button_terms.state(['disabled'])
            self.terms_entry.state(['!disabled'])
        else:
            self.terms_file_entry.state(['!disabled'])
            self.button_terms.state(['!disabled'])
            self.terms_entry.state(['disabled'])
    def open_file(self):
        self.link_file.set(filedialog.askopenfilename())
    def open_file_blacklist(self):
        self.blacklist_file.set(filedialog.askopenfilename())
    def open_file_blacklisted(self):
        self.blacklisted_file.set(filedialog.asksaveasfile().name)
    def open_file_terms(self):
        self.terms_file.set(filedialog.askopenfilename())
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
            columns_values.update([['terms',self.terms_s.get()]])
            config={
                'crawl':self.crawl.get(),
                'sitemap':self.sitemap.get(),
                'catalog':self.catalog.get(),
                'term':terms,
                'use_terms':self.blacklist.get(),
                'terms':self.terms_file.get(),
                'columns':columns_values,
                'use_links':self.link.get(),
                'blacklist':self.blacklist_file.get(),
                'use_blacklist':self.blacklist.get(),
                'blacklist_output':self.blacklisted_file.get(),
                'use_blacklist_output':self.blacklisted.get(),
                'links':self.link_file.get(),
                'max':int(self.max.get()),
                }
            with open('config.json','w') as f:
                f.write(json.dumps(config))
            self.root.destroy()


root = Tk()
c=ConfigScraper(root)
root.bind("<Return>", c.save)
root.mainloop()
