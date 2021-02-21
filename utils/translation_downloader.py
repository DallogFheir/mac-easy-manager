import aiohttp
from argparser import parser
import asyncio
from bs4 import BeautifulSoup
from io import BytesIO
import json
import logging
import re
import time
import zipfile

# functions
async def main(num_of_workers):
    start = time.perf_counter()
    logging.info("Started program...")

    res = await get_translations(num_of_workers)

    translations = {}
    translations["by_code"] = {}
    translations["by_name"] = {}

    res.sort(key=lambda k: k[0]) # sort by language name
    for data in res:
        name, code, trans = data
        translations["by_code"][code] = name
        translations["by_name"][name] = {cont:translation for cont, translation in trans}

    with open("container_translations.json","w",encoding="utf-8") as f:
        json.dump(translations,f)

    duration = time.perf_counter() - start
    logging.info(f"Completed in {duration} s.")

async def get_translations(num_of_workers):
    queues = {
        q: asyncio.Queue()
        for q in ("langpack_rows","lang_packs", "install_links", "xpi_files")
    }
    result_queue = asyncio.Queue()

    async with aiohttp.ClientSession(raise_for_status=True) as session:
        tasks = [
                asyncio.create_task(get_lang_pack_links(queues["langpack_rows"],queues["lang_packs"])) 
                for _ in range(num_of_workers)
        ] + [
            asyncio.create_task(get_install_link(session,queues["lang_packs"],queues["install_links"])) 
            for _ in range(num_of_workers)
        ] + [
            asyncio.create_task(get_xpi_file(session,queues["install_links"],queues["xpi_files"]))
            for _ in range(num_of_workers)
        ] + [
            asyncio.create_task(get_translation(queues["xpi_files"],result_queue))
            for _ in range(num_of_workers)
        ]
        main_producer = asyncio.create_task(get_lang_pack_page(session,queues["langpack_rows"]))

        await main_producer
        for queue in queues.values():
            await queue.join()
        for task in tasks:
            task.cancel()

    res = []
    while True:
        try:
            item = result_queue.get_nowait()
            res.append(item)
        except asyncio.QueueEmpty:
            break

    return res

# single-task coroutines
async def get_lang_pack_page(session,langpack_row_q):
    r = await session.get("https://addons.mozilla.org/en-US/firefox/language-tools/")
    content = await r.read()

    soup = BeautifulSoup(content,"lxml")
    rows = soup.select("[data-testid='tbody'] > tr")

    for row in rows:
        await langpack_row_q.put(row)

async def get_lang_pack_links(langpack_row_q,lang_pack_q):
    while True:
        row : BeautifulSoup = await langpack_row_q.get()

        if (link := row.select(":scope > td:nth-child(2) > ul > li > a")):
            lang_name = row.select(":scope > td:first-child > strong")[0].text
            url = "https://addons.mozilla.org/" + link[0]["href"] # link to add-on install page

            logging.debug(f"Got language pack link for {lang_name}.")

            await lang_pack_q.put((lang_name,url))

        langpack_row_q.task_done()

async def get_install_link(session,lang_pack_q,install_link_q):
    while True:
        lang_name, url = await lang_pack_q.get()

        r = await session.get(url)
        content = await r.read()

        soup = BeautifulSoup(content, "lxml")
        install_link = soup.select(".InstallButtonWrapper-download-link")[0]["href"]


        logging.debug(f"Got install link for {lang_name}.")

        await install_link_q.put((lang_name,install_link))

        lang_pack_q.task_done()

async def get_xpi_file(session,install_link_q,file_q):
    while True:
        lang_name, url = await install_link_q.get()

        r = await session.get(url)
        content = await r.read()

        xpi_file = BytesIO(content)

        logging.debug(f"Got XPI file for {lang_name}.")

        await file_q.put((lang_name,xpi_file))

        install_link_q.task_done()

async def get_translation(file_q,res_q):
    while True:
        lang_name, file = await file_q.get()

        with zipfile.ZipFile(file) as zip_file:
                # path = browser/chrome/{language abbreviation}/locale/browser/browser.properties
                path = zipfile.Path(zip_file,"browser/chrome/")
                lang_code = list(path.iterdir())[0].name # middle folder
                
                new_path = f"browser/chrome/{lang_code}/locale/browser/browser.properties"

                with zip_file.open(new_path) as browser_properties:
                    translations = re.findall(
                        r"""
                        # userContextPersonal.label = Pa ngat moni
                        userContext
                        (Personal|Work|Banking|Shopping|None)
                        \.
                        label
                        \ = \ 
                        (.*?)
                        \n
                        """,
                        browser_properties.read().decode("utf-8"),
                        flags=re.X
                    )

        logging.info(f"Got translations for {lang_name}.")

        await res_q.put((lang_name, lang_code, translations))
        
        file_q.task_done()

if __name__ == "__main__":
    args_dict = vars(parser.parse_args())

    logging.basicConfig(level=args_dict["log"],format="%(message)s")

    # asyncio.run results in RuntimeError: Event loop is closed
    loop = asyncio.get_event_loop()
    loop.set_debug(args_dict["debug"])
    loop.run_until_complete(main(args_dict["workers"]))
