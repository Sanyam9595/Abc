from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re

#----------------------------------------------------------------------------------------------------------------------
def post_data_contains_all_search_queries(post_title, post_content, search_queries: list[str]):
    """Function checks posts tile or content contains all given search query"""
    search_result = post_title + post_content
    
    for search_query in search_queries:
        if search_query.lower() not in search_result.lower():
            # If search result don't contains all search queries
            return False
        
        if "stock market" in post_title.lower():
            # Skipping this posts
            return False

    # If search result contains all search queries
    return True

#----------------------------------------------------------------------------------------------------------------------
def scrape_reddit_search_data(driver, url):
    """
    Function to open reddit search page and scrap the data from it
    """
    try:
        driver.get(url)
        time.sleep(1) # let the page load.

        # Getting all post Data
        posts = driver.find_elements(By.TAG_NAME, "search-telemetry-tracker")

        # Storing scrapped data in list
        data_list = []
        for post in posts:
            if post.text:
                post_data = post.text.split('\n')
                if len(post_data) >= 4 and " ago" in post_data[3]:
                    data_list.append({
                        "title"         : post_data[0],
                        "time_lapsed"   : post_data[3],
                        "post_link"     : post.find_element(By.TAG_NAME, 'a').get_attribute("href")
                    })                  
        return data_list
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

#----------------------------------------------------------------------------------------------------------------------
def scrap_reddit_post_content(url):
    """Function used to scrap post content from give reddit post"""
    try:
        # Send a GET request to fetch the page content
        response = requests.get(url)

        # Parse the page content with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the div with the specific id
        div = soup.find('div', id=re.compile(r't3_.*-post-rtjson-content$'))
    
        # Extract and print the text from each <p> tag
        return "\n".join([p.get_text().strip() for p in div.find_all('p')]) if div else ""
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return ""
    
#----------------------------------------------------------------------------------------------------------------------
def convert_time_lapsed_to_datetime(time_lapsed):
    """Function to convert the time_lapsed to a datetime object"""
    try:
        time_lapsed = time_lapsed.replace(" ago", "")

        # Example conversion for 'h ago', 'd ago', etc.
        time_units = {'h': 'hours', 'd': 'days', 'm': 'minutes', 'mo': 'month'}

        for i in range(len(time_lapsed)):
            if not time_lapsed[i].isdigit():
                amount = int(time_lapsed[:i])
                unit = time_lapsed[i:]
                break
        
        # Converting month to days considering 1 month = 30 days
        if unit == 'mo':
            amount *= 30
            unit = 'd'

        delta = pd.Timedelta(**{time_units[unit]: amount})
        return datetime.now() - delta
    except Exception as e:
        print(f"Error in converting time: {e}")
        return None
    
#######################################################################################################################
#######################################################################################################################
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
reddit_search_URL = "https://www.reddit.com/search?q={}&t={}"

group_1_search_queries = ["GLP-1", "GLP1", "Wegovy", "Ozempic", "Zepbound"]
group_2_search_queries = ["Optum", "United", "UHC", "CVS", "Caremark", "Aetna", "Express Scripts", "ESI", "Cigna"]

time_interval = 'month' # => 'day', 'week', 'month'

# creating search queries
search_queries_list = []
for g1_search_query in group_1_search_queries:
    for g2_search_query in group_2_search_queries:
        search_queries_list.append((g1_search_query, g2_search_query))


# Prepare the data to be written into the Excel
data = []
for search_queries in search_queries_list:

    print(f"Scrapping data for post having {', '.join(search_queries)} words in it.")

    # Creating URL
    url = reddit_search_URL.format("+".join(search_queries), time_interval)

    # Scrapping Data in list(Dictioanries containing posts data) format
    scrapped_data = scrape_reddit_search_data(driver = driver, url = url)
    
    # Appending data to list
    for post_data in scrapped_data:
        group1_word = search_queries[0]
        group2_word = search_queries[1]
        title = post_data['title']
        datetime_of_post = convert_time_lapsed_to_datetime(time_lapsed = post_data['time_lapsed'])
        link =  post_data['post_link']
        content = scrap_reddit_post_content(url = post_data['post_link'])
        key_points = None  # Will fill this later (Using Open AI)

        if content.startswith("https://"):
            content = "*" + content

        # Checking if post is valid
        if post_data_contains_all_search_queries(post_title = title,
                                                 post_content = content,
                                                 search_queries = search_queries):
            # Add the data row to the list 
            data.append([group1_word, group2_word, datetime_of_post, link, title, content, key_points])
        
# Closing Selenium driver
driver.quit()

# Create a DataFrame from the data list and wirting it to an Excel file
df = pd.DataFrame(data, columns=["group_1 word", "group_2 word", "datetime of post", "Link", "Title", "Content", "Key points"])
df.to_excel("scraped_data.xlsx", index=False)
print("Data has been written to 'scraped_data.xlsx'")
