from configparser import ConfigParser
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
from PIL import ImageTk
import re
import shutil
import tkinter as tk
from tkinter import ttk, messagebox
import traceback

#region EXCEPTION HANDLER
# taken from here: https://mail.python.org/pipermail/python-list/2001-March/104202.html
class TkErrorCatcher:
    def __init__(self,func,subst,widget):
        self.func = func
        self.subst = subst
        self.widget = widget
    def __call__(self, *args):
        try:
             if self.subst:
                 args = self.subst(*args)
             return self.func(*args)
        except:
            messagebox.showwarning("Error!",f"Unknown error happened!\n{traceback.format_exc()}")
tk.CallWrapper = TkErrorCatcher
#endregion

class MACEasyManager:
    def __init__(self):
        # path to Firefox data folder on Windows
        # C:\Users\{user}\AppData\Roaming\Mozilla\Firefox
        self.folder_path = Path(Path.home() / Path("AppData", "Roaming", "Mozilla", "Firefox"))

        # Tkinter init
        self.root = tk.Tk()

        self.root.title("MAC Easy Manager")

        icon = ImageTk.PhotoImage(file="icons/icon.ico")
        self.root.iconphoto(True,icon) # True to be default for all toplevels

        # get system resolution to position window
        self.screen_width=self.root.winfo_screenwidth()
        self.screen_height=self.root.winfo_screenheight()

        # load GUI vars from file
        with open("config/gui_config.json",encoding="utf-8") as f:
            self.gui_vars = json.load(f)

        self.profile_select_window()
        self.root.focus_force() # to focus after reinitialization
        self.root.mainloop()

    #region GUI METHODS
    def profile_select_window(self):
        # frame
        self.profile_select_frame = tk.Frame(self.root)
        self.profile_select_frame.pack(padx=self.gui_vars["pad"]["x"],pady=self.gui_vars["pad"]["y"])

        # header
        tk.Label(self.profile_select_frame,text=self.gui_vars["text"]["profile_select_window"]["header"],font=self.gui_vars["font"]["header"]).pack(pady=self.gui_vars["pad"]["y"])

        # info about default profile
        tk.Label(self.profile_select_frame,text=self.gui_vars["text"]["profile_select_window"]["subheader"],font=self.gui_vars["font"]["small_text"],fg=self.gui_vars["color"]["small_text"]).pack()

        # separator
        ttk.Separator(self.profile_select_frame, orient="horizontal").pack(fill="x",pady=self.gui_vars["pad"]["y"])

        #region RADIOBUTTONS
        self.get_profiles()

        # before if because used by get_def_languages
        self.profile_radiobtn_var = tk.StringVar()
        # if no profiles found
        if not self.prof_dict:
            tk.Label(self.profile_select_frame,text=self.gui_vars["text"]["profile_select_window"]["no_profs"],font=self.gui_vars["font"]["normal"],fg=self.gui_vars["color"]["warn"]).pack()
        # if there are profiles
        else:
            # in case default profile is empty
            # make default button the 1st one
            default_button = list(self.prof_dict.keys())[0]

            # creates buttons
            for profile in self.prof_dict:
                cur_btn = tk.Radiobutton(self.profile_select_frame,variable=self.profile_radiobtn_var,value=profile,text=profile,font=self.gui_vars["font"]["normal"],command=self.get_def_language)

                # if profile is default, makes text bold
                if self.prof_dict[profile]["is_default"]:
                    cur_btn.config(font=self.gui_vars["font"]["default_profile"])

                    default_button = profile

                cur_btn.pack()

            # invokes default button
            self.profile_radiobtn_var.set(default_button)
        #endregion

        # separator
        ttk.Separator(self.profile_select_frame, orient="horizontal").pack(fill="x",pady=self.gui_vars["pad"]["y"])

        # Select button
        # continues to main window
        # is focused on start
        select_button = tk.Button(self.profile_select_frame,text=self.gui_vars["text"]["button"]["select"],font=self.gui_vars["font"]["normal"],command=self.main_window)
        select_button.pack()

        # if there are no profiles, disable the button
        if not self.profile_radiobtn_var.get():
            select_button.config(state="disabled")
        else:
            select_button.focus()
            # binds Enter to button action
            self.root.bind("<Return>",lambda *_: select_button.invoke())

        #region IGNORE CONTAINERS OPTION
        # frame
        ignore_frame = tk.Frame(self.profile_select_frame)
        ignore_frame.pack()

        # checkbutton
        self.if_ignored = tk.IntVar()

        ignore_button = tk.Checkbutton(ignore_frame,text=self.gui_vars["text"]["button"]["ignore"],font=self.gui_vars["font"]["normal"],variable=self.if_ignored)
        ignore_button.pack(side="left",pady=self.gui_vars["pad"]["y"])

        ignore_button.invoke()

        # entrybox
        self.ignore_entrybox = tk.Entry(ignore_frame,font=self.gui_vars["font"]["normal"])
        self.ignore_entrybox.pack(side="right",pady=self.gui_vars["pad"]["y"])
        # default ignored container: "tmp"
        # from Temporary Containers extension
        self.ignore_entrybox.insert(0,"tmp")

        # regex checkbutton
        self.if_regex = tk.IntVar()

        tk.Checkbutton(self.profile_select_frame,text=self.gui_vars["text"]["button"]["regex"],font=self.gui_vars["font"]["small_text"],variable=self.if_regex).pack()

        # ignore case checkbutton
        self.if_ignore_case = tk.IntVar()

        tk.Checkbutton(self.profile_select_frame,text=self.gui_vars["text"]["button"]["ignore_case"],font=self.gui_vars["font"]["small_text"],variable=self.if_ignore_case).pack()
        
        # info about ignore
        tk.Label(self.profile_select_frame,text=self.gui_vars["text"]["profile_select_window"]["ignore_info"],font=self.gui_vars["font"]["small_text"],fg=self.gui_vars["color"]["small_text"]).pack(pady=self.gui_vars["pad"]["y"])
        #endregion

        #region LANGUAGE SELECT OPTION
        # separator
        ttk.Separator(self.profile_select_frame, orient="horizontal").pack(fill="x",pady=self.gui_vars["pad"]["y"])

        # option menu
        with open("config/container_translations.json",encoding="utf-8") as f:
            self.translation_data = json.load(f)
        
        self.language_select_var = tk.StringVar()

        self.language_select = ttk.Combobox(self.profile_select_frame,textvariable=self.language_select_var,values=list(self.translation_data["by_name"].keys()),state="readonly")
        self.language_select.config(font=self.gui_vars["font"]["normal"])
        self.language_select.pack(pady=self.gui_vars["pad"]["y"])

        # perform function on load
        self.get_def_language()

        # info
        tk.Label(self.profile_select_frame,text=self.gui_vars["text"]["profile_select_window"]["language_select_info_1"],font=self.gui_vars["font"]["small_text"],fg=self.gui_vars["color"]["small_text"]).pack(pady=self.gui_vars["pad"]["y"])
        tk.Label(self.profile_select_frame,text=self.gui_vars["text"]["profile_select_window"]["language_select_info_2"],font=self.gui_vars["font"]["small_text"],fg=self.gui_vars["color"]["small_text"]).pack()
        #endregion

        #region WINDOW POSITION
        # get window size
        self.root.update_idletasks() #update idletasks to get correct size
        win_width=self.root.winfo_width()
        win_height=self.root.winfo_height()
        # calculate position
        # half screen resolution - half window size
        half_width=int(self.screen_width/2-win_width/2)
        half_height=int(self.screen_height/2-win_height/2)
        # position window
        # "+X_position+Y_position"
        self.root.geometry(f"+{str(half_width)}+{str(half_height)}")
        #endregion
    def main_window(self):
        # unbinds Enter from Select button
        self.root.unbind("<Return>")

        # removes profile selection window
        self.profile_select_frame.pack_forget()

        # gets path of selected profile
        self.sel_prof_path = self.prof_dict[self.profile_radiobtn_var.get()]["path"]

        # gets ignored container name
        self.ignored_str = self.ignore_entrybox.get()

        # loads container icons
        self.icon_imgs = {}
        icon_path = Path("icons", "container_icons")
        # icons > container_icons > {color} > {icon}.png
        for icon_folder in icon_path.iterdir():
            for icon in icon_folder.iterdir():
                # name of icon = {color}{icon}
                self.icon_imgs[f"{icon_folder.name}{icon.stem}"] = ImageTk.PhotoImage(file=icon)

        # loads default order
        with open("default_order.json",encoding="utf-8") as f:
            self.default_order = json.load(f)
            # gets current order from default order
            self.current_order = deepcopy(self.default_order)
        with open("config/original_order.json",encoding="utf-8") as f:
            self.orig_order = json.load(f)

        #region GUI
        # supermain frame to center content
        self.super_frame = tk.Frame(self.root)
        self.super_frame.pack()

        # main frames
        # canvas to add scrollbar
        # highlightthickness to remove border
        self.main_frame = tk.Canvas(self.super_frame,highlightthickness=0)
        self.main_frame.pack(side="left")

        # wrapper frame
        # needed a wrapper to draw inside of canvas to be scrollable
        self.wrapper_frame = tk.Frame(self.main_frame)
        self.main_frame.create_window((0,0),window=self.wrapper_frame)

        # 0 y-padding at bottom
        self.top_frame = tk.Frame(self.wrapper_frame)
        self.top_frame.pack(padx=self.gui_vars["pad"]["main_x"],pady=(self.gui_vars["pad"]["main_y"],0),fill="x")

        ttk.Separator(self.wrapper_frame,orient="horizontal").pack(fill="x")

        self.bottom_frame = tk.Frame(self.wrapper_frame)
        self.bottom_frame.pack(padx=self.gui_vars["pad"]["main_x"],pady=self.gui_vars["pad"]["main_y"],fill="x")

        # main scrollbar
        self.main_scrollbar = tk.Scrollbar(self.super_frame)
        self.main_scrollbar.pack(side="left",fill="y")
        self.main_scrollbar.config(command=self.main_frame.yview)
        self.main_frame.config(yscrollcommand=self.main_scrollbar.set)
        # bind <Configure> (= changing size) to change scroll region of canvas
        self.wrapper_frame.bind("<Configure>",lambda *_: self.main_frame.configure(scrollregion=self.main_frame.bbox("all")))
        
        #region TOP FRAME
        #region LIST OF CONTAINERS
        # frame
        self.containers_frame = tk.Frame(self.top_frame)
        self.containers_frame.pack(side="left",padx=self.gui_vars["pad"]["main_x"],pady=self.gui_vars["pad"]["main_y"],anchor="n")

        # title
        tk.Label(self.containers_frame,text=self.gui_vars["text"]["main_window"]["containers"],font=self.gui_vars["font"]["header"]).grid(**self.gui_vars["grid"]["containers_frame"]["title"])

        # treeview
        # selectmode:
        # extended = multiple selections
        # show:
        # tree = without header
        self.cont_treeview = ttk.Treeview(self.containers_frame,height=13,selectmode="extended",show="tree")
        self.cont_treeview.grid(**self.gui_vars["grid"]["containers_frame"]["treeview"])

        # binds selecting item in treeview to enable current container edit box and disable move up/down button if 1st or last item selected
        self.cont_treeview.bind("<<TreeviewSelect>>",self.cont_handle_select)
        # binds toggle_bind_treeview on hovering over/out to allow scrolling
        self.cont_treeview.bind("<Enter>",self.toggle_bind_treeview)
        self.cont_treeview.bind("<Leave>",self.toggle_bind_treeview)

        # fixes rowheight to be readable
        # once for all treeviews
        ttk.Style().configure("Treeview",rowheight=30)
        
        # scrollbar
        self.cont_treeview_scrollbar=tk.Scrollbar(self.containers_frame)
        self.cont_treeview_scrollbar.grid(**self.gui_vars["grid"]["containers_frame"]["scrollbar"])
        self.cont_treeview.config(yscrollcommand = self.cont_treeview_scrollbar.set)
        self.cont_treeview_scrollbar.config(command = self.cont_treeview.yview)

        # move up and down buttons
        # disabled at start
        self.cont_move_up_btn=tk.Button(self.containers_frame,text=self.gui_vars["text"]["button"]["move_up"],font=self.gui_vars["font"]["normal"],command=self.cont_move_up)
        self.cont_move_up_btn.config(state="disabled") 
        self.cont_move_up_btn.grid(**self.gui_vars["grid"]["containers_frame"]["move_up"])

        self.cont_move_down_btn=tk.Button(self.containers_frame,text=self.gui_vars["text"]["button"]["move_down"],font=self.gui_vars["font"]["normal"],command=self.cont_move_down)
        self.cont_move_down_btn.config(state="disabled") 
        self.cont_move_down_btn.grid(**self.gui_vars["grid"]["containers_frame"]["move_down"])

        # Restore original order button
        tk.Button(self.containers_frame,text=self.gui_vars["text"]["button"]["restore_cont"],font=self.gui_vars["font"]["normal"],command=self.cont_restore).grid(**self.gui_vars["grid"]["containers_frame"]["restore"])

        # Restored label (shown for 1 second when restored)
        self.cont_restored_label = tk.Label(self.containers_frame,font=self.gui_vars["font"]["normal"])
        self.cont_restored_label.grid(**self.gui_vars["grid"]["containers_frame"]["saved"])
        #endregion
        #region SORTING OPTIONS
        # frame
        self.sorting_options_frame = tk.Frame(self.top_frame)
        self.sorting_options_frame.pack(side="left",anchor="n")

        # PRIMARY SORTING
        # frame
        self.prim_sort_options_frame = tk.Frame(self.sorting_options_frame)
        self.prim_sort_options_frame.pack(padx=self.gui_vars["pad"]["main_x"],pady=self.gui_vars["pad"]["main_y"])

        # title
        tk.Label(self.prim_sort_options_frame,text=self.gui_vars["text"]["main_window"]["primary_sort"],font=self.gui_vars["font"]["header"]).pack()

        # radiobuttons
        self.prim_sort = tk.StringVar()
        self.prim_sort_lst = []

        for i, v in enumerate(["name", "color", "icon"]):
            self.prim_sort_lst.append(tk.Radiobutton(self.prim_sort_options_frame,text=v,font=self.gui_vars["font"]["normal"],variable=self.prim_sort,value=i,command=self.handle_sorting_options))
            self.prim_sort_lst[i].pack()

        # select no button at start
        self.prim_sort.set(None)

        # reverse checkbutton
        # reverse list for all 3 reverse checkbuttons
        self.reverse_lst = [tk.IntVar() for _ in range(3)]

        tk.Checkbutton(self.prim_sort_options_frame,text=self.gui_vars["text"]["main_window"]["reverse"],font=self.gui_vars["font"]["normal"],variable=self.reverse_lst[0],command=self.sort).pack()

        # SECONDARY SORTING
        # frame
        self.sec_sort_options_frame = tk.Frame(self.sorting_options_frame)
        self.sec_sort_options_frame.pack(padx=self.gui_vars["pad"]["main_x"],pady=self.gui_vars["pad"]["main_y"])

        # title
        tk.Label(self.sec_sort_options_frame,text=self.gui_vars["text"]["main_window"]["secondary_sort"],font=self.gui_vars["font"]["header"]).pack(side="top")

        # radiobuttons
        self.sec_sort = tk.StringVar()
        # has to be StringVar because None for IntVar is 0, which messes up sort
        self.sec_sort_lst = []

        for i, v in enumerate(["name", "color", "icon"]):
            self.sec_sort_lst.append(tk.Radiobutton(self.sec_sort_options_frame,text=v,font=self.gui_vars["font"]["normal"],variable=self.sec_sort,value=i,state="disabled",command=self.handle_sorting_options))
            self.sec_sort_lst[i].pack()
        
        # select no button at start
        self.sec_sort.set(None)

        # reverse checkbutton
        tk.Checkbutton(self.sec_sort_options_frame,text=self.gui_vars["text"]["main_window"]["reverse"],font=self.gui_vars["font"]["normal"],variable=self.reverse_lst[1],command=self.sort).pack()

        # TERTIARY SORTING
        # frame
        self.tert_sort_options_frame = tk.Frame(self.sorting_options_frame)
        self.tert_sort_options_frame.pack(padx=self.gui_vars["pad"]["main_x"],pady=self.gui_vars["pad"]["main_y"])

        # title
        tk.Label(self.tert_sort_options_frame,text=self.gui_vars["text"]["main_window"]["tertiary_sort"],font=self.gui_vars["font"]["header"]).pack(side="top")

        # reverse checkbutton
        tk.Checkbutton(self.tert_sort_options_frame,text=self.gui_vars["text"]["main_window"]["reverse"],font=self.gui_vars["font"]["normal"],variable=self.reverse_lst[2],command=self.sort).pack()

        # SAVE & RESTORE
        # frame
        self.save_sorting_frame = tk.Frame(self.sorting_options_frame)
        self.save_sorting_frame.pack(padx=self.gui_vars["pad"]["main_x"],pady=self.gui_vars["pad"]["main_y"])

        tk.Button(self.save_sorting_frame,text=self.gui_vars["text"]["button"]["save_options"],font=self.gui_vars["font"]["normal"],command=self.save_sorting_options).pack(pady=self.gui_vars["pad"]["y"])

        tk.Button(self.save_sorting_frame,text=self.gui_vars["text"]["button"]["load_options"],font=self.gui_vars["font"]["normal"],command=self.sort_opts_restore).pack(pady=self.gui_vars["pad"]["y"])

        self.sort_saved_label = tk.Label(self.save_sorting_frame,font=self.gui_vars["font"]["normal"])
        self.sort_saved_label.pack(pady=self.gui_vars["pad"]["y"])

        #endregion
        #region COLOR SORT
        # frame
        self.color_frame = tk.Frame(self.top_frame)
        self.color_frame.pack(side="left",padx=self.gui_vars["pad"]["main_x"],pady=self.gui_vars["pad"]["main_y"],anchor="n")

        # title
        tk.Label(self.color_frame,text=self.gui_vars["text"]["main_window"]["color"],font=self.gui_vars["font"]["header"]).grid(**self.gui_vars["grid"]["containers_frame"]["title"])

        # treeview
        # selectmode:
        # browse = single selection
        # extended = multiple selections
        # show:
        # tree = without header
        self.color_treeview = ttk.Treeview(self.color_frame,height=13,selectmode="extended",show="tree")
        self.color_treeview.grid(**self.gui_vars["grid"]["containers_frame"]["treeview"])

        # binds selecting item in treeview to enable current container edit box and disable move up/down button if 1st or last item selected
        self.color_treeview.bind("<<TreeviewSelect>>",self.color_handle_select)
        
        # move up and down buttons
        # disabled at start
        self.color_move_up_btn=tk.Button(self.color_frame,text=self.gui_vars["text"]["button"]["move_up"],font=self.gui_vars["font"]["normal"],command=self.color_move_up)
        self.color_move_up_btn.config(state="disabled") 
        self.color_move_up_btn.grid(**self.gui_vars["grid"]["containers_frame"]["move_up"])

        self.color_move_down_btn=tk.Button(self.color_frame,text=self.gui_vars["text"]["button"]["move_down"],font=self.gui_vars["font"]["normal"],command=self.color_move_down)
        self.color_move_down_btn.config(state="disabled") 
        self.color_move_down_btn.grid(**self.gui_vars["grid"]["containers_frame"]["move_down"])

        # Reset to original order button
        tk.Button(self.color_frame,text=self.gui_vars["text"]["button"]["reset_cont"],font=self.gui_vars["font"]["normal"],command=self.color_reset).grid(**self.gui_vars["grid"]["containers_frame"]["reset"])

        # Restore default order button
        tk.Button(self.color_frame,text=self.gui_vars["text"]["button"]["restore_cont"],font=self.gui_vars["font"]["normal"],command=self.color_restore).grid(**self.gui_vars["grid"]["containers_frame"]["restore"])

        # Save as default button
        tk.Button(self.color_frame,text=self.gui_vars["text"]["button"]["save_default"],font=self.gui_vars["font"]["normal"],command=self.color_save_order).grid(**self.gui_vars["grid"]["containers_frame"]["save"])

        # Saved/Restored label (shown for 1 second when saved/restored)
        self.color_saved_label = tk.Label(self.color_frame,font=self.gui_vars["font"]["normal"])
        self.color_saved_label.grid(**self.gui_vars["grid"]["containers_frame"]["saved"])
        #endregion
        #region ICON SORT
        # frame
        self.icon_frame = tk.Frame(self.top_frame)
        self.icon_frame.pack(side="left",padx=self.gui_vars["pad"]["main_x"],pady=self.gui_vars["pad"]["main_y"],anchor="n")

        # title
        tk.Label(self.icon_frame,text=self.gui_vars["text"]["main_window"]["icon"],font=self.gui_vars["font"]["header"]).grid(**self.gui_vars["grid"]["containers_frame"]["title"])

        # treeview
        # selectmode:
        # browse = single selection
        # extended = multiple selections
        # show:
        # tree = without header
        self.icon_treeview = ttk.Treeview(self.icon_frame,height=13,selectmode="extended",show="tree")
        self.icon_treeview.grid(**self.gui_vars["grid"]["containers_frame"]["treeview"])

        # binds selecting item in treeview to enable current container edit box and disable move up/down button if 1st or last item selected
        self.icon_treeview.bind("<<TreeviewSelect>>",self.icon_handle_select)
        
        # move up and down buttons
        # disabled at start
        self.icon_move_up_btn=tk.Button(self.icon_frame,text=self.gui_vars["text"]["button"]["move_up"],font=self.gui_vars["font"]["normal"],command=self.icon_move_up)
        self.icon_move_up_btn.config(state="disabled") 
        self.icon_move_up_btn.grid(**self.gui_vars["grid"]["containers_frame"]["move_up"])

        self.icon_move_down_btn=tk.Button(self.icon_frame,text=self.gui_vars["text"]["button"]["move_down"],font=self.gui_vars["font"]["normal"],command=self.icon_move_down)
        self.icon_move_down_btn.config(state="disabled") 
        self.icon_move_down_btn.grid(**self.gui_vars["grid"]["containers_frame"]["move_down"])

        # Reset to original order button
        tk.Button(self.icon_frame,text=self.gui_vars["text"]["button"]["reset_cont"],font=self.gui_vars["font"]["normal"],command=self.icon_reset).grid(**self.gui_vars["grid"]["containers_frame"]["reset"])

        # Restore original order button
        tk.Button(self.icon_frame,text=self.gui_vars["text"]["button"]["restore_cont"],font=self.gui_vars["font"]["normal"],command=self.icon_restore).grid(**self.gui_vars["grid"]["containers_frame"]["restore"])

        # Save as default button
        tk.Button(self.icon_frame,text=self.gui_vars["text"]["button"]["save_default"],font=self.gui_vars["font"]["normal"],command=self.icon_save_order).grid(**self.gui_vars["grid"]["containers_frame"]["save"])

        # Saved/Restored label (shown for 1 second when saved/restored)
        self.icon_saved_label = tk.Label(self.icon_frame,font=self.gui_vars["font"]["normal"])
        self.icon_saved_label.grid(**self.gui_vars["grid"]["containers_frame"]["saved"])
        #endregion
        #endregion

        #region BOTTOM FRAME
        #region CONTAINER EDIT
        # frame
        self.cont_edit_frame = tk.Frame(self.bottom_frame)
        self.cont_edit_frame.pack(side="left")

        #region CURRENT CONTAINER
        # frame
        self.cur_cont_frame = tk.Frame(self.cont_edit_frame)
        self.cur_cont_frame.pack(pady=self.gui_vars["pad"]["y"],anchor="w")

        # label
        tk.Label(self.cur_cont_frame,text=self.gui_vars["text"]["main_window"]["cur_cont"],font=self.gui_vars["font"]["header"]).pack(side="left")

        # icon
        # none at start
        self.cur_cont_icon = tk.Label(self.cur_cont_frame)
        self.cur_cont_icon.pack(side="left")

        # name
        # "none" at start
        self.cur_cont_name = tk.Label(self.cur_cont_frame,text=self.gui_vars["text"]["main_window"]["cur_cont_name"],font=self.gui_vars["font"]["normal"])
        self.cur_cont_name.pack(side="left")
        #endregion
        #region CHANGE NAME
        # frame
        self.change_name_frame = tk.Frame(self.cont_edit_frame)
        self.change_name_frame.pack(pady=self.gui_vars["pad"]["y"],anchor="w")

        # label
        tk.Label(self.change_name_frame,text=self.gui_vars["text"]["main_window"]["cur_cont_change_name"],font=self.gui_vars["font"]["normal"]).pack(side="left",padx=self.gui_vars["pad"]["x"])

        # entrybox
        self.change_name_var = tk.StringVar()

        self.change_name_entry = tk.Entry(self.change_name_frame,state="disabled",font=self.gui_vars["font"]["normal"],textvariable=self.change_name_var)
        self.change_name_entry.pack(side="left",padx=self.gui_vars["pad"]["x"])

        # bind change of input to black font
        # font is grey when entry is "(multiple)"
        self.change_name_var.trace_add("write",lambda *_: self.change_name_entry.config(fg="black"))
        # bind clicking on input so that "(multiple)"" disappears when clicked
        self.change_name_entry.bind("<Button-1>",lambda *_: self.change_name_var.get() == "(multiple)" and self.change_name_var.set(""))

        # "Press Enter" info
        tk.Label(self.change_name_frame,text=self.gui_vars["text"]["main_window"]["cur_cont_change_name_info"],font=self.gui_vars["font"]["small_text"],fg=self.gui_vars["color"]["small_text"]).pack(side="left")
        #endregion
        #region CHANGE COLOR
        # frame
        self.change_color_frame = tk.Frame(self.cont_edit_frame)
        self.change_color_frame.pack(pady=self.gui_vars["pad"]["y"],anchor="w")

        # label
        tk.Label(self.change_color_frame,text=self.gui_vars["text"]["main_window"]["cur_cont_change_color"],font=self.gui_vars["font"]["normal"]).pack(side="left",padx=self.gui_vars["pad"]["x"])

        # color images
        self.change_color_lst = []

        for i, color in enumerate(self.orig_order["color"]):
            # disabled at start
            # image name = {color}circle
            self.change_color_lst.append(tk.Button(self.change_color_frame,image=self.icon_imgs[color+"circle"],borderwidth=0,state="disabled",command=lambda i=color: self.change_color(i)))
            self.change_color_lst[i].pack(side="left",padx=self.gui_vars["pad"]["small_icon_x"])
        #endregion
        #region CHANGE ICON
        # frame
        self.change_icon_frame = tk.Frame(self.cont_edit_frame)
        self.change_icon_frame.pack(pady=self.gui_vars["pad"]["y"],anchor="w")

        # label
        tk.Label(self.change_icon_frame,text=self.gui_vars["text"]["main_window"]["cur_cont_change_icon"],font=self.gui_vars["font"]["normal"]).pack(side="left",padx=self.gui_vars["pad"]["x"])

        # icon images
        self.change_icon_lst = []

        for i, icon in enumerate(self.orig_order["icon"]):
            # disabled at start
            # image name = toolbar{icon}
            self.change_icon_lst.append(tk.Button(self.change_icon_frame,image=self.icon_imgs["toolbar"+icon],borderwidth=0,state="disabled",command=lambda i=icon : self.change_icon(i)))
            self.change_icon_lst[i].pack(side="left",padx=self.gui_vars["pad"]["small_icon_x"])
        #endregion
        #region DELETE & ADD BUTTONS
        # frame
        self.del_add_btns_frame = tk.Frame(self.cont_edit_frame)
        self.del_add_btns_frame.pack(pady=self.gui_vars["pad"]["y"])

        # Delete button
        # disabled at start
        self.del_button = tk.Button(self.del_add_btns_frame,text=self.gui_vars["text"]["button"]["delete"],font=self.gui_vars["font"]["normal"],state="disabled",command=self.delete_cont)
        self.del_button.pack(side="left",padx=self.gui_vars["pad"]["x"])

        # Add a new container
        self.add_button = tk.Button(self.del_add_btns_frame,text=self.gui_vars["text"]["button"]["add"],font=self.gui_vars["font"]["normal"],command=self.add_cont)
        self.add_button.pack(side="left",padx=self.gui_vars["pad"]["x"])
        # sets focus to button
        self.add_button.focus()
        #endregion
        #endregion
        #region SAVE & BACK BUTTON
        # frame
        self.save_back_frame = tk.Frame(self.bottom_frame)
        self.save_back_frame.pack(side="right",padx=self.gui_vars["pad"]["x"])

        # Save button
        tk.Button(self.save_back_frame,text=self.gui_vars["text"]["button"]["save"],font=self.gui_vars["font"]["normal"],command=self.save).pack(pady=self.gui_vars["pad"]["y"])

        # Back to profile selection button
        tk.Button(self.save_back_frame,text=self.gui_vars["text"]["button"]["back"],font=self.gui_vars["font"]["normal"],command=self.back_to_profile).pack(pady=self.gui_vars["pad"]["y"])
        #endregion
        #endregion
        #endregion

        # binds mouse click to set focus on widget
        # to toggle Enter bind to Add a container button & changing name of current container
        self.root.bind_all("<Button-1>",lambda event: event.widget.focus_set())
        self.change_name_entry.bind("<FocusIn>",self.toggle_bind_entrybox)
        self.change_name_entry.bind("<FocusOut>",self.toggle_bind_entrybox)
        # calls initial toggle_bind_entrybox/treeview
        self.if_toggled_entrybox = True
        self.toggle_bind_entrybox()
        self.if_toggled_treeview = False
        self.toggle_bind_treeview()

        # perform start-up methods
        self.get_containers()
        self.refresh_conts()
        self.refresh_colors()
        self.refresh_icons()

        # removes selection from container treeview
        # (because at start if_added gets triggered because start length = 0)
        self.cont_treeview.selection_remove(self.cont_treeview.selection())
        # scroll to top
        self.cont_treeview.yview_moveto(0)

        # marks as saved
        self.if_saved = True

        #region WINDOW POSITION
        # get size of wrapper frame
        self.wrapper_frame.update_idletasks()
        win_width = self.wrapper_frame.winfo_width()
        win_height = self.wrapper_frame.winfo_height()
        # if frame size is bigger than 80% of screen size, uses screen size instead
        if win_width > self.screen_width or win_height > self.screen_height:
            win_width=int(self.screen_width * 0.8)
            win_height=int(self.screen_height * 0.8)
        # calculate position
        # half screen resolution - half window size
        half_width=int(self.screen_width/2-win_width/2)
        half_height=int(self.screen_height/2-win_height/2)
        # position window
        # "{width}x{height}+{X_position}+{Y_position}"
        # +20 for scrollbar
        self.root.geometry(f"{win_width+20}x{win_height}+{half_width}+{half_height}")
        # config canvas to fit window
        self.main_frame.config(width=win_width,height=win_height)
        #endregion

        # handle quitting program
        self.root.protocol("WM_DELETE_WINDOW",self.close)

    def toggle_bind_entrybox(self,*_):
        # if Change name entrybox is unfocused
        if self.if_toggled_entrybox:
            # unbinds Enter from saving Change name entrybox
            self.change_name_entry.unbind("<Return>")

            # binds Enter to invoke Add a new container button
            # and sets focus to it
            self.root.bind("<Return>",lambda *_: self.add_button.invoke())
            self.add_button.focus()

            # binds Ctrl+A to select all containers in Containers treeview
            self.root.bind("<Control-a>",lambda *_: self.cont_treeview.selection_set(self.cont_treeview.get_children()))

            # binds Delete to Delete button
            # (works even before 1st selection, because button is disabled)
            self.root.bind("<Delete>",lambda *_: self.del_button.invoke())

            # toggles if_toggled_entrybox
            self.if_toggled_entrybox = False

        # if Change name entrybox is focused
        else:
            # unbinds Enter from Add a new container button
            self.root.unbind("<Return>")

            # unbinds Ctrl+A from selecting all containers in Containers treeview
            # so that it works for selecting whole text in Change name entrybox
            self.root.unbind("<Control-a>")

            # unbinds Delete to Delete button
            self.root.unbind("<Delete>")

            # binds Enter to save name in Change name entry
            self.change_name_entry.bind("<Return>",self.change_name)

            # toggles if_toggled_entrybox
            self.if_toggled_entrybox = True
    def toggle_bind_treeview(self,*_):
        # if containers treeview is unfocused
        if self.if_toggled_treeview:
            # unbind mouse wheel to scroll window so that user can scroll treeview
            self.root.unbind_all("<MouseWheel>")

            # toggles if_toggled_treeview
            self.if_toggled_treeview = False

        # if containers treeview is focused
        else:
            # bind mouse wheel to root to scroll anywhere
            # taken from here: https://stackoverflow.com/a/17457843
            self.root.bind_all("<MouseWheel>",lambda event: self.main_frame.yview_scroll(int(-1*event.delta/120),"units"))

            # toggles if_toggled_treeview
            self.if_toggled_treeview = True

    def back_to_profile(self):
        if self.check_if_saved():
            # reinitalizes program
            self.root.destroy()
            self.__init__()
    def close(self):
        if self.check_if_saved():
            # quits program
            self.root.destroy()
            self.root.quit()
    #endregion

    #region SORTING METHODS
    def handle_sorting_options(self):
        # gets selected button in Primary sorting
        cur_btn = self.prim_sort.get()

        # makes all Secondary sorting buttons enabled
        for btn in self.sec_sort_lst:
            btn.config(state="normal")

        # if Primary == Secondary or no Secondary selected, selects next one
        if self.sec_sort.get() in [cur_btn, "None"]:
            self.sec_sort.set((int(cur_btn)+1)%3)

        # disables Secondary button with same value as Primary
        self.sec_sort_lst[int(cur_btn)].config(state="disabled")

        # sorts containers
        self.sort()

    def sort(self):
        # has to check if sorting option is selected
        # because moving colors/icon up/down calls sort too
        if self.prim_sort.get() != "None":
            # dictionary to map sorting options to functions
            # 0 : name (case insensitive)
            # 1 : color = turns color name into number, given by order in sorting order
            # 2 : icon = turns icon name into number, given by order in sorting order
            sort_func_dict = {
                0 : lambda cont: cont["name"].lower(),
                1 : lambda cont: self.current_order["color"].index(cont["color"]),
                2 : lambda cont: self.current_order["icon"].index(cont["icon"])
            }

            # gets 1st and 2nd sorting option from buttons
            # 3rd sorting option from set difference
            # (tuple to get value as int)
            first_sort = int(self.prim_sort.get())
            second_sort = int(self.sec_sort.get())
            third_sort = tuple({0, 1, 2}.difference({first_sort, second_sort}))[0]

            sort_options_lst = [first_sort, second_sort, third_sort]

            # turns ints from sort_options_lst to functions in sort_func_dict
            sort_func_lst = [sort_func_dict[option] for option in sort_options_lst]

            # handles reverse sorting
            # reverse sorting names has to be handled by built-in reverse keyword
            # sets reverse to True if Reverse checkbutton for sorting name (0 in options list) is checked
            # checkbutton IntVar = 1 if selected, 0 if not
            reverse = self.reverse_lst[sort_options_lst.index(0)].get()

            for index, option in enumerate(sort_options_lst):
                # if option is not sorting by name (0)
                if option:
                    # if button is unchecked (0) and reverse==True
                    # (because reverse will be handled by reverse keyword in sort, so unchecked options have to be reversed to be sorted normally)
                    # or button is checked (1) and reverse==False
                    if self.reverse_lst[index].get() != reverse:
                        # makes function return opposite number to sort number
                        # so that it will sort in opposite direction
                        sort_func_lst[index] = lambda cont, func=sort_func_lst[index]: -func(cont)

            # performs sort with key being list of sorting indexes/names
            self.ready_conts.sort(key=lambda cont: [func(cont) for func in sort_func_lst],reverse=reverse)

        # refreshes container treeview
        self.refresh_conts()
    #endregion

    #region GET METHODS
    def get_profiles(self):
        # gets profiles.ini file from Firefox data folder
        # C:\Users\{user}\AppData\Roaming\Mozilla\Firefox
        # if file/folder doesn't exist, ConfigParser handles it internally
        config = ConfigParser()
        config.read(self.folder_path / "profiles.ini")

        #region FILE STRUCTURE
        # [Install208046BA024A39CB]
        # Default=Profiles/asd213.default-release (< PATH TO DEFAULT PROFILE)
        # Locked=1

        # [Profile2]
        # Name=something
        # IsRelative=0
        # Path=C:\Users\User\1231sad.something

        # [Profile1]
        # Name=default
        # IsRelative=1
        # Path=Profiles/12321asd.default
        # Default=1 (! THIS DOES NOT CHANGE WITH DEFAULT PROFILE CHANGE)
        #endregion
        
        # prevents unbound
        default = None
        # gets default profile from [Install] section
        for section in config.sections():
            if re.match("Install",section):
                default = config[section]["Default"]
                break

        # gets all profiles names and paths from [ProfileN] sections
        profile_dict = {}

        for section in config.sections():
            if re.match("Profile",section):
                # gets path
                path = config[section]["Path"]
                # if path is relative, adds full folder path
                full_path = self.folder_path / path if config[section]["isRelative"] else Path(path)

                # checks if profile is not empty
                if Path.exists(full_path / "containers.json"):
                    name = config[section]["Name"]
                    is_default = path==default

                    # profile name is unique
                    # creates profile_dict
                    profile_dict[name] = {}
                    profile_dict[name]["path"] = full_path
                    profile_dict[name]["is_default"] = is_default   

        self.prof_dict = profile_dict 
    
    def get_containers(self):
        # loads whole containers.json file
        with open(self.sel_prof_path / "containers.json",encoding="utf-8") as f:
            self.raw_conts = json.load(f)

        #region FILE STRUCTURE
        # {
        # "version": 4,
        # "lastUserContextId": 6,
        # "identities": [
        #     {
        #     "userContextId": 1,
        #     "public": true,
        #     "icon": "fingerprint",
        #     "color": "blue",
        #     "l10nID": "userContextPersonal.label",
        #     "accessKey": "userContextPersonal.accesskey",
        #     "telemetryId": 1
        #     },
        #     {
        #     "userContextId": 2,
        #     "public": true,
        #     "icon": "briefcase",
        #     "color": "orange",
        #     "l10nID": "userContextWork.label",
        #     "accessKey": "userContextWork.accesskey",
        #     "telemetryId": 2
        #     },
        #     {
        #     "userContextId": 3,
        #     "public": true,
        #     "icon": "dollar",
        #     "color": "green",
        #     "l10nID": "userContextBanking.label",
        #     "accessKey": "userContextBanking.accesskey",
        #     "telemetryId": 3
        #     },
        #     {
        #     "userContextId": 4,
        #     "public": true,
        #     "icon": "cart",
        #     "color": "pink",
        #     "l10nID": "userContextShopping.label",
        #     "accessKey": "userContextShopping.accesskey",
        #     "telemetryId": 4
        #     },
        #     {
        #     "userContextId": 5,
        #     "public": false,
        #     "icon": "",
        #     "color": "",
        #     "name": "userContextIdInternal.thumbnail",
        #     "accessKey": ""
        #     },
        #     {
        #     "userContextId": 4294967295,
        #     "public": false,
        #     "icon": "",
        #     "color": "",
        #     "name": "userContextIdInternal.webextStorageLocal",
        #     "accessKey": ""
        #     },
        #     {
        #     "userContextId": 6,
        #     "public": true,
        #     "icon": "dollar",
        #     "color": "green",
        #     "name": "Custom"
        #     }
        # ]
        # }
        #endregion

        # gets ignored name/regex pattern
        # ignored name = {input} followed by any number of digits
        # if regex chosen, doesn't add default pattern
        added_regex = "" if self.if_regex else r"(\d+|$)"
        # if ignore case, adds re.I flag
        pattern_str = self.ignored_str + added_regex
        pattern = re.compile(pattern_str,re.I) if self.if_ignore_case.get() else re.compile(pattern_str)

        self.ready_conts = []
        self.ignored_conts = []

        for identity in self.raw_conts["identities"]:
            # ignores non-public identities
            if identity["public"]:
                # adds name to default containers with only AccessKey
                # userContextPersonal.accessKey, userContextBanking.accessKey etc.
                if "accessKey" in identity:
                    # translates them to selected language
                    lang = self.language_select_var.get()
                    cont = re.search(r"userContext(.*)?.accesskey",identity["accessKey"]).group(1)

                    identity["name"] = self.translation_data["by_name"][lang][cont]
                
                # puts ignored names into ignored_conts list
                if self.if_ignored.get() and re.fullmatch(pattern,identity["name"]):
                    self.ignored_conts.append(identity)
                else:
                    # else appends to main list ready_conts
                    self.ready_conts.append(identity)
            else:
                # if identity is not public, appends to ignored_conts
                self.ignored_conts.append(identity)

        # creates a deepcopy to compare to ready_cont to check if saved
        self.orig_conts = deepcopy(self.ready_conts)

        # gets last ID
        self.last_id = self.raw_conts["lastUserContextId"]
    
    def get_def_language(self):
        # if any profile exists
        # otherwise default to en-US
        main_lang = "en-US"
        if self.profile_radiobtn_var.get():
            # get Firefox's language for selected profile
            # in user.js (may not exist) or prefs.js
            # user_pref("intl.locale.requested", "en-US,ast")
            cur_prof_path = self.prof_dict[self.profile_radiobtn_var.get()]["path"]

            user_path = cur_prof_path / "user.js"

            pref_path = user_path if user_path.exists() else cur_prof_path / "prefs.js"

            lang_pref_pattern = re.compile(r'user_pref\("intl\.locale\.requested", "(.*?)"\)')

            with open(pref_path,encoding="utf-8") as f:
                lang_settings = re.search(lang_pref_pattern,f.read())
                # the setting may not exist if there's only 1 language
                if lang_settings is not None:
                    all_langs = lang_settings.group(1)
                    main_lang = all_langs.split(",")[0]

        self.language_select_var.set(self.translation_data["by_code"][main_lang])
    #endregion
    
    #region REFRESH METHODS
    def refresh_conts(self,if_deleted=None):
        selections = self.cont_treeview.selection()

        # gets current items to compare if any items were added/deleted
        # and to find next item after the one deleted
        orig_items = self.cont_treeview.get_children()

        next_item = None
        if selections:
            # gets highest index among selected items
            max_index = max([self.cont_treeview.index(selection) for selection in selections])

            # gets next item after last one selected (if it's not last)
            # to select if selected items are deleted
            if max_index != len(orig_items)-1:
                next_item = (self.cont_treeview.get_children()[max_index+1],)
            # else next_item is set to last item in new treeview after repopulating
                
        # clears treeview
        self.cont_treeview.delete(*self.cont_treeview.get_children())

        # repopulates treeview
        # args = parent ("" = new toplevel entry), index, id (= userContextId)
        for container in self.ready_conts:
            self.cont_treeview.insert("","end",container["userContextId"],text=container["name"],image=self.icon_imgs[container["color"]+container["icon"]])

        # checks if items were added/deleted
        new_items = self.cont_treeview.get_children()
        if_added = len(orig_items) < len(new_items)
        if if_deleted is None:
            if_deleted = len(orig_items) > len(new_items)
        # checks if containers were restored (are same as original list)
        # then it needs to ignore if_added
        # (which is triggered if containers were deleted)
        # changes if_saved boole if current items are different from original original
        self.if_saved = self.ready_conts==self.orig_conts

        # disables Current container and Delete if empty
        if len(new_items) == 0:
            # disables Current container icon and name
            self.cur_cont_icon.config(image="")
            self.cur_cont_name.config(text="none")

            # empties and disables Change name entrybox
            self.change_name_entry.delete(0,"end")
            self.change_name_entry.config(state="disabled")

            # disables Change color/icon buttons
            for btn in self.change_color_lst:
                btn.config(state="disabled")

            for btn in self.change_icon_lst:
                btn.config(state="disabled")

            # disables Delete buttons
            self.del_button.config(state="disabled")
        # if not empty, if there is selection (deleting also requires selection) or new container was added, restores selection
        elif selections or if_added:
            # gets original IDs as a tuple to compare to selection
            orig_conts_items = tuple(str(cont["userContextId"]) for cont in self.orig_conts)
            # if original containers were restored, only select those previously selected that are in orig conts
            # ignore added conts
            if new_items==orig_conts_items and not if_deleted:
                selections = tuple(selection for selection in selections if selection in orig_conts_items)

            elif if_added and not self.if_saved:
                # gets added container's ID from difference of current items and orig_items
                # tuple to get value as int
                added_item = tuple(set(new_items).difference(set(orig_items)))[0]
                # overwrites selection with added item
                selections = (added_item,)

            elif if_deleted:
                # set next_item to last item if it's None
                if next_item is None:
                    next_item = (self.cont_treeview.get_children()[-1],)

                selections = next_item

            # selects either previous selection, or added item, or next after last deleted item
            self.cont_treeview.selection_set(selections)

            # scroll to (1st) selection if not visible
            # (condition to handle 1st time loading, when there is no selection but if_saved is True)
            if selections:
                self.cont_treeview.see(selections[0])

    def refresh_colors(self):
        selections = self.color_treeview.selection()

        # clears treeview
        self.color_treeview.delete(*self.color_treeview.get_children())

        # repopulates treeview
        # args = parent ("" = new toplevel entry), index, id (= color)
        for color in self.current_order["color"]:
            self.color_treeview.insert("","end",color,text=color,image=self.icon_imgs[color+"circle"])

        # restores selection
        # checks if there is selection to not trigger color_handle_select
        if selections:
            self.color_treeview.selection_set(selections)
    
    def refresh_icons(self):
        selections = self.icon_treeview.selection()

        # clears treeview
        self.icon_treeview.delete(*self.icon_treeview.get_children())

        # repopulates treeview
        # args = parent ("" = new toplevel entry), index, id (= icon)
        for icon in self.current_order["icon"]:
            self.icon_treeview.insert("","end",icon,text=icon,image=self.icon_imgs["toolbar"+icon])
    
        # restore selection
        # checks if there is selection to not trigger icon_handle_select
        if selections:
            self.icon_treeview.selection_set(selections)
    #endregion

    #region SELECT METHODS
    def cont_handle_select(self,*_):
        selections = self.cont_treeview.selection()

        # prevents unbound
        cont_name = "none"
        fg = "black"
        # handles start case when there is no selection
        if selections:
            # gets indexes to check if selection can be moved up and down
            indices = [self.cont_treeview.index(selection) for selection in selections]
            
            # if 1 item is selected
            if len(selections) == 1:
                # finds container of given ID in ready_conts
                for container in self.ready_conts:
                    if container["userContextId"] == int(selections[0]):
                        # modifies Current container's name and icon
                        cont_name = container["name"]
                        self.cur_cont_name.config(text=cont_name)
                        self.cur_cont_icon.config(image=self.icon_imgs[container["color"]+container["icon"]])
                        # font color = black
                        fg = "black"
                        break
            # if multiple items are selected
            else:
                # checks if all selected items have same name/color/icon
                # by adding them to sets
                name_set = set()
                color_set = set()
                icon_set = set()
                for item_id in selections:
                    for container in self.ready_conts:
                        if container["userContextId"] == int(item_id):
                            name_set.add(container["name"])
                            color_set.add(container["color"])
                            icon_set.add(container["icon"])

                # if all selected items have same name, show that name
                if len(name_set) == 1:
                    cont_name = tuple(name_set)[0]
                    fg = "black"
                # else, show "(multiple)" in grey
                else:
                    cont_name = f'({self.gui_vars["text"]["main_window"]["cur_cont_name_multiple"]})'
                    fg = "grey"

                only_color = tuple(color_set)[0]
                only_icon = tuple(icon_set)[0]
                # default color & icon
                color_name = "toolbar"
                icon_name = "default"
                # if all items have same color, show it
                if len(color_set)==1:
                    color_name = only_color
                # if all items have same icon, show it
                if len(icon_set)==1:
                    icon_name = only_icon

                # sets name and icon
                self.cur_cont_name.config(text=cont_name)
                # if items don't have same color & icon, set container icon to nothing
                if [color_name, icon_name] == ["toolbar", "default"]:
                    self.cur_cont_icon.config(image="")
                else:
                    self.cur_cont_icon.config(image=self.icon_imgs[color_name+icon_name])

            # enables Change color/icon buttons
            for button in self.change_color_lst:
                button.config(state="normal")
            for button in self.change_icon_lst:
                button.config(state="normal")

            # enables Change name entrybox, sets it to container name
            self.change_name_var.set(cont_name)
            self.change_name_entry.config(state="normal",fg=fg)

            # enables Delete button
            self.del_button.config(state="normal")

            # checks if selection can be moved up and down
            # compares minimal index to 0
            if min(indices)==0:
                self.cont_move_up_btn.config(state="disabled")
            else:
                self.cont_move_up_btn.config(state="normal")
            
            # compares maximal index to length of treeview
            if max(indices)==len(self.cont_treeview.get_children())-1:
                self.cont_move_down_btn.config(state="disabled")
            else:
                self.cont_move_down_btn.config(state="normal")
        
    def color_handle_select(self,*_):
        selections = self.color_treeview.selection()
        # gets indexes to check if selection can be moved up and down
        indices = [self.color_treeview.index(selection) for selection in selections]

        # checks if can be moved up and down
        # compares minimal index to 0
        if min(indices)==0:
            self.color_move_up_btn.config(state="disabled")
        else:
            self.color_move_up_btn.config(state="normal")

        # compares maximal index to length of treeview
        if max(indices)==len(self.color_treeview.get_children())-1:
            self.color_move_down_btn.config(state="disabled")
        else:
            self.color_move_down_btn.config(state="normal")
    
    def icon_handle_select(self,_):
        selections = self.icon_treeview.selection()
        # gets indexes to check if selection can be moved up and down
        indices = [self.icon_treeview.index(selection) for selection in selections]

        # checks if can be moved up and down
        # compares minimal index to 0
        if min(indices)==0:
            self.icon_move_up_btn.config(state="disabled")
        else:
            self.icon_move_up_btn.config(state="normal")

                # compares maximal index to length of treeview

                # compares maximal index to length of treeview

        # compares maximal index to length of treeview
        if max(indices)==len(self.icon_treeview.get_children())-1:
            self.icon_move_down_btn.config(state="disabled")
        else:
            self.icon_move_down_btn.config(state="normal")
    #endregion

    #region MOVE UP & DOWN METHODS
    def cont_move_up(self):
        selections = self.cont_treeview.selection()

        # finds selected container and exchanges it with container below
        for ind, container in enumerate(self.ready_conts):
            if str(container["userContextId"]) in selections:
                self.ready_conts[ind], self.ready_conts[ind-1] = self.ready_conts[ind-1], self.ready_conts[ind]

        # refreshes treeview
        self.refresh_conts()

        # deselects sorting radiobuttons
        self.prim_sort.set(None)
        self.sec_sort.set(None)
        # disables Secondary radiobuttons
        for btn in self.sec_sort_lst:
            btn.config(state="disabled")
    def cont_move_down(self):
        selections = self.cont_treeview.selection()

        # finds selected container and exchanges it with container below
        # has to go through list in reverse
        for container in self.ready_conts[::-1]:
            if str(container["userContextId"]) in selections:
                ind = self.ready_conts.index(container)
                self.ready_conts[ind], self.ready_conts[ind+1] = self.ready_conts[ind+1], self.ready_conts[ind]

        self.refresh_conts()

        # deselect sorting radiobuttons
        self.prim_sort.set(None)
        self.sec_sort.set(None)
        for btn in self.sec_sort_lst:
            btn.config(state="disabled")
        selection_item = self.cont_treeview.selection()
        selection_id = int(selection_item[0])

    def color_move_up(self):
        selections = self.color_treeview.selection()

        # finds selected color and exchanges it with color below
        for ind, color in enumerate(self.current_order["color"]):
            if color in selections:
                self.current_order["color"][ind], self.current_order["color"][ind-1] = self.current_order["color"][ind-1], self.current_order["color"][ind]

        # refreshes color treeview and sorts
        self.refresh_colors()
        self.sort()
    def color_move_down(self):
        selections = self.color_treeview.selection()

        # finds selected color and exchanges it with color below
        # has to go through list in reverse
        for color in self.current_order["color"][::-1]:
            if color in selections:
                ind = self.current_order["color"].index(color)
                self.current_order["color"][ind], self.current_order["color"][ind+1] = self.current_order["color"][ind+1], self.current_order["color"][ind]

        # refreshes color treeview and sorts
        self.refresh_colors()
        self.sort()

    def icon_move_up(self):
        selections = self.icon_treeview.selection()

        # finds selected icon and exchanges it with icon below
        for ind, icon in enumerate(self.current_order["icon"]):
            if icon in selections:
                self.current_order["icon"][ind], self.current_order["icon"][ind-1] = self.current_order["icon"][ind-1], self.current_order["icon"][ind]

        # refreshes icon treeview and sorts
        self.refresh_icons()
        self.sort()
    def icon_move_down(self):
        selections = self.icon_treeview.selection()

        # finds selected icon and exchanges it with icon below
        # has to go through list in reverse
        for icon in self.current_order["icon"][::-1]:
            if icon in selections:
                ind = self.current_order["icon"].index(icon)
                self.current_order["icon"][ind], self.current_order["icon"][ind+1] = self.current_order["icon"][ind+1], self.current_order["icon"][ind]

                # refreshes color treeview and sorts

                # refreshes color treeview and sorts

                # refreshes color treeview and sorts

        # refreshes icon treeview and sorts
        self.refresh_icons()
        self.sort()
    #endregion

    #region RESET ORIGINAL ORDER METHODS
    def color_reset(self):
        # makes current order a deepcopy of original order
        self.current_order["color"] = deepcopy(self.orig_order["color"])

        # refreshes color treeview
        self.sort()
        self.refresh_colors()

        # shows Reset! label
        self.color_saved_label.config(text=self.gui_vars["text"]["main_window"]["reset"])
        # after 1 second, removes text
        self.color_saved_label.after(self.gui_vars["timer"],lambda: self.color_saved_label.config(text=""))
    
    def icon_reset(self):
        # makes current order a deepcopy of original order
        self.current_order["icon"] = deepcopy(self.orig_order["icon"])

        # refreshes icon treeview
        self.sort()
        self.refresh_icons()

        # shows Reset! label
        self.icon_saved_label.config(text=self.gui_vars["text"]["main_window"]["reset"])
        # after 1 second, removes text
        self.icon_saved_label.after(self.gui_vars["timer"],lambda: self.icon_saved_label.config(text=""))
    #endregion
    #region RESTORE DEFAULT ORDER METHODS
    def cont_restore(self):
        # check if new containers have been added/containers have been edited by simulated set difference
        # (sets can't be used because dictionaries are not hashable)
        changed_conts = [cont for cont in self.ready_conts if cont not in self.orig_conts]
        # gets deleted containers too
        deleted_conts = [cont for cont in self.orig_conts if cont not in self.ready_conts]

        # if added/changed/deleted, show a warning message
        if changed_conts or deleted_conts:
            # messagebox returns true or false
            # if user answers No, stops function
            if not messagebox.askyesno(title=self.gui_vars["text"]["added_warning"]["title"],message=self.gui_vars["text"]["added_warning"]["message"]):
                return

        self.get_containers()
        self.refresh_conts()

        # show Restored! label
        self.cont_restored_label.config(text=self.gui_vars["text"]["main_window"]["restored"])
        # after 1 second, removes text
        self.cont_restored_label.after(self.gui_vars["timer"],lambda: self.cont_restored_label.config(text=""))

        # deselects sorting radiobuttons
        self.prim_sort.set(None)
        self.sec_sort.set(None)
        # disables Secondary radiobuttons
        for btn in self.sec_sort_lst:
            btn.config(state="disabled")

    def sort_opts_restore(self):
        if not Path("sorting_options.json").exists():
            return messagebox.showwarning(**self.gui_vars["text"]["no_sort_options"])

        with open("sorting_options.json") as f:
            opts = json.load(f)

        prim, prim_rev = opts["primary"]
        self.prim_sort.set(prim)
        self.reverse_lst[0].set(prim_rev)

        sec, sec_rev = opts["secondary"]
        self.sec_sort.set(sec)
        self.reverse_lst[1].set(sec_rev)

        self.reverse_lst[2].set(opts["tertiary"])

        self.sort()

        # shows Restored! label
        self.sort_saved_label.config(text=self.gui_vars["text"]["main_window"]["loaded"])
        # after 1 second, removes text
        self.sort_saved_label.after(self.gui_vars["timer"],lambda: self.sort_saved_label.config(text=""))

    def color_restore(self):
        # makes current order a deepcopy of default order
        self.current_order["color"] = deepcopy(self.default_order["color"])

        # refreshes color treeview
        self.refresh_colors()
        self.sort()

        # shows Restored! label
        self.color_saved_label.config(text=self.gui_vars["text"]["main_window"]["restored"])
        # after 1 second, removes text
        self.color_saved_label.after(self.gui_vars["timer"],lambda: self.color_saved_label.config(text=""))

    def icon_restore(self):
        # makes current order a deepcopy of default order
        self.current_order["icon"] = deepcopy(self.default_order["icon"])

        # refreshes icon treeview
        self.refresh_icons()
        self.sort()

        # shows Restored! label
        self.icon_saved_label.config(text=self.gui_vars["text"]["main_window"]["restored"])
        # after 1 second, removes text
        self.icon_saved_label.after(self.gui_vars["timer"],lambda: self.icon_saved_label.config(text=""))
    #endregion
    #region SAVE DEFAULT ORDER METHODS
    def save_sorting_options(self):
        opts = {
            "primary" : [
                self.prim_sort.get(),
                self.reverse_lst[0].get()
            ],
            "secondary" : [
                self.sec_sort.get(),
                self.reverse_lst[1].get()
            ],
            "tertiary" : self.reverse_lst[2].get()
        }

        with open("sorting_options.json","w",encoding="utf-8") as f:
            json.dump(opts,f)
    
        # shows Saved! label
        self.sort_saved_label.config(text=self.gui_vars["text"]["main_window"]["saved"])
        # after 1 second, removes text
        self.sort_saved_label.after(self.gui_vars["timer"],lambda: self.sort_saved_label.config(text=""))

    def color_save_order(self):
        # deepcopies current order to default order
        self.default_order["color"] = deepcopy(self.current_order["color"])

        # saves default order to config file
        with open('default_order.json','w',encoding="utf-8") as f:
            json.dump(self.default_order,f)
        
        # shows Saved! label
        self.color_saved_label.config(text=self.gui_vars["text"]["main_window"]["saved"])
        # after 1 second, removes text
        self.color_saved_label.after(self.gui_vars["timer"],lambda: self.color_saved_label.config(text=""))

    def icon_save_order(self):
        # deepcopies current order to default order
        self.default_order["icon"] = deepcopy(self.current_order["icon"])

        # saves default order to config file
        with open('default_order.json','w',encoding="utf-8") as f:
            json.dump(self.default_order,f)

        # shows Saved! label
        self.icon_saved_label.config(text=self.gui_vars["text"]["main_window"]["saved"])
        # after 1 second, removes text
        self.icon_saved_label.after(self.gui_vars["timer"],lambda: self.icon_saved_label.config(text=""))
    #endregion

    #region EDIT CONTAINER METHODS
    def change_name(self,*_):
        selections = self.cont_treeview.selection()
        # gets name from Change name entrybox
        name = self.change_name_entry.get()

        for container in self.ready_conts:
            if str(container["userContextId"]) in selections:
                # if container is default, removes "l10nID" and "accessKey" keys
                if "accessKey" in container:
                    del container["accessKey"]
                    del container["l10nID"]
                container["name"] = name
        
        self.sort()
    def change_color(self,color):
        selections = self.cont_treeview.selection()
        
        for container in self.ready_conts:
            if str(container["userContextId"]) in selections:
                container["color"] = color
        
        self.sort()
    def change_icon(self,icon):
        selections = self.cont_treeview.selection()
        
        for container in self.ready_conts:
            if str(container["userContextId"]) in selections:
                container["icon"] = icon

        self.sort()
    
    def delete_cont(self):
        selections = self.cont_treeview.selection()

        # temp_lst to avoid iterating over list and deleting its items
        temp_lst = deepcopy(self.ready_conts)

        for container in temp_lst:
            if str(container["userContextId"]) in selections:
                self.ready_conts.remove(container)

        # doesn't need to sort, order same
        self.refresh_conts(if_deleted=True)
    #endregion

    #region ADD CONTAINER POPUP
    def add_cont(self):
        # popup
        self.add_popup=tk.Toplevel()
        self.add_popup.title(self.gui_vars["text"]["add_popup"]["title"])

        # main frame
        self.add_popup_frame = tk.Frame(self.add_popup)
        self.add_popup_frame.pack(padx=self.gui_vars["pad"]["x"],pady=self.gui_vars["pad"]["y"])

        #region NAME
        # frame
        self.add_name_frame = tk.Frame(self.add_popup_frame)
        self.add_name_frame.pack(pady=self.gui_vars["pad"]["y"],anchor="w")

        # label
        tk.Label(self.add_name_frame,text=self.gui_vars["text"]["add_popup"]["name"],font=self.gui_vars["font"]["normal"]).pack(side="left",padx=self.gui_vars["pad"]["x"])

        # entrybox
        self.add_name_var = tk.StringVar()
        # check if name is not empty
        self.add_name_var.trace_add("write",self.add_check)

        self.add_name_entry = tk.Entry(self.add_name_frame,font=self.gui_vars["font"]["normal"],textvariable=self.add_name_var)
        self.add_name_entry.pack(side="left",padx=self.gui_vars["pad"]["x"])

        # sets focus to entrybox
        self.add_name_entry.focus()
        #endregion
        #region COLOR
        # frame
        self.add_color_frame = tk.Frame(self.add_popup_frame)
        self.add_color_frame.pack(pady=self.gui_vars["pad"]["y"],anchor="w")

        # label
        tk.Label(self.add_color_frame,text=self.gui_vars["text"]["add_popup"]["color"],font=self.gui_vars["font"]["normal"]).pack(side="left",padx=self.gui_vars["pad"]["x"])

        # buttons
        self.add_color_lst = []

        for index, color in enumerate(self.orig_order["color"]):
            # command gets index to modify button
            self.add_color_lst.append(tk.Button(self.add_color_frame,image=self.icon_imgs[color+"circle"],borderwidth=0,command=lambda i=index, j=color: self.add_color_update(i,j)))

            self.add_color_lst[index].pack(side="left",padx=self.gui_vars["pad"]["small_icon_x"])
        #endregion
        #region ICON
        # frame
        self.add_icon_frame = tk.Frame(self.add_popup_frame)
        self.add_icon_frame.pack(pady=self.gui_vars["pad"]["y"],anchor="w")

        # label
        tk.Label(self.add_icon_frame,text=self.gui_vars["text"]["add_popup"]["icon"],font=self.gui_vars["font"]["normal"]).pack(side="left",padx=self.gui_vars["pad"]["x"])

        # buttons
        self.add_icon_lst = []

        for index, icon in enumerate(self.orig_order["icon"]):
            # command gets index to modify button
            self.add_icon_lst.append(tk.Button(self.add_icon_frame,image=self.icon_imgs["toolbar"+icon],borderwidth=0,command=lambda i=index, j=icon : self.add_icon_update(i,j)))

            self.add_icon_lst[index].pack(side="left",padx=self.gui_vars["pad"]["small_icon_x"])
        #endregion

        #region ADD BUTTON
        # frame
        self.add_add_button_frame = tk.Frame(self.add_popup_frame)
        self.add_add_button_frame.pack(pady=self.gui_vars["pad"]["y"])

        # button
        self.add_add_button = tk.Button(self.add_add_button_frame,text=self.gui_vars["text"]["add_popup"]["add"],state="disabled",command=self.add_cont_save)
        self.add_add_button.pack(pady=self.gui_vars["pad"]["y"])

        # bind Enter to button
        self.add_popup.bind("<Return>",lambda *_: self.add_add_button.invoke())
        #endregion

        #region WINDOW POSITION
        # get window size
        self.add_popup.update_idletasks() #update idletasks to get correct size
        add_width=self.add_popup.winfo_width()
        add_height=self.add_popup.winfo_height()
        # calculate position
        # half screen resolution - half window size
        half_width=int(self.screen_width/2-add_width/2)
        half_height=int((self.screen_height-40)/2-add_height/2)
        # makes window not resizable above max size
        # self.add_popup.maxsize(add_width,add_height)
        # makes window not resizable at all
        self.add_popup.resizable(False,False)
        # position window
        # "+X_position+Y_position"
        self.add_popup.geometry("+"+str(half_width)+"+"+str(half_height))
        
        # sets focus to window
        self.add_popup.focus()
        #endregion

        # sets default values
        self.add_icon = None
        self.add_color = None

    def add_color_update(self,index,color):
        self.add_color = color

        # unsinks and unborders all buttons
        for btn in self.add_color_lst:
            btn.config(relief="flat",borderwidth=0)

        # sinks and borders selected button
        self.add_color_lst[index].config(relief="sunken",borderwidth=1)

        # checks if entry can be added (name and icons are selected)
        self.add_check()
    def add_icon_update(self,index,icon):
        self.add_icon = icon

        # unsinks and unborders all buttons
        for btn in self.add_icon_lst:
            btn.config(relief="flat",borderwidth=0)

        # sinks and borders selected button
        self.add_icon_lst[index].config(relief="sunken",borderwidth=1)

        # checks if entry can be added (name and color are selected)
        self.add_check()
    def add_check(self,*_):
        # gets name from Name entrybox
        self.add_name = self.add_name_entry.get()

        # if color & icon are selected and name is not empty, enables Add button
        if self.add_color and self.add_icon and self.add_name:
            self.add_add_button.config(state="normal")
        else:
        # else disables Add button
            self.add_add_button.config(state="disabled")
            
    def add_cont_save(self):
        self.last_id += 1

        temp_con = {}
        temp_con["userContextId"] = self.last_id
        temp_con["public"] = True
        temp_con["icon"] = self.add_icon
        temp_con["color"] = self.add_color
        temp_con["name"] = self.add_name_entry.get()

        self.ready_conts.append(deepcopy(temp_con))
        self.sort()

        self.add_popup.destroy()
    #endregion

    #region SAVE METHODS
    def check_if_saved(self):
        if self.if_saved:
            return True
        else:
            # messagebox returns True or False
            return messagebox.askyesno(**self.gui_vars["text"]["save_warning"])

    def save(self):
        ready_output = deepcopy(self.ready_conts)

        # removes "name" property if "accessKey" is present
        for container in ready_output:
            if "accessKey" in container:
                del container["name"]

        # appends ignored containers to ready containers
        identities_output = ready_output + self.ignored_conts

        # gets entire raw file
        output = deepcopy(self.raw_conts)
        # updates containers
        output["identities"] = deepcopy(identities_output)
        # updates lastUserContextId
        output["lastUserContextId"] = self.last_id

        # creates backup with name:
        # {profile}_{DD-MM-YY_HH-MM-SS}.json
        backup_filename = f'{self.profile_radiobtn_var.get()}_{datetime.now().strftime("%d-%m-%Y_%H-%M-%S")}.json'

        backup_path = Path("backups")
        if not backup_path.exists():
            backup_path.mkdir()

        shutil.copy(self.sel_prof_path / "containers.json", backup_path / backup_filename)

        # saves file
        with open(self.sel_prof_path / "containers.json","w",encoding="utf-8") as f:
            json.dump(output,f)

        # shows Success message
        messagebox.showinfo(**self.gui_vars["text"]["save_success"])

        self.if_saved = True
    #endregion
