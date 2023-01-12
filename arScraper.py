from urllib.request import urlopen
from bs4 import BeautifulSoup as Soup
import time
import jellyfish

#Number of recipes stored on each page of results by allrecipes website.
RESULT_OFFSET_SIZE = 24

#Allowed Jaro similarity between two strings for them to be considered the same ingredient/unit.
ING_SIM_ALLOWANCE = 0.25
UNIT_SIM_ALLOWANCE = 0.35

#HTML classes/id tags used by allRecipes
CLASS_RECIPE_CARD   = "comp mntl-card-list-items mntl-document-card mntl-card card card--no-image"
CLASS_RECIPE_RATING = "recipe-card-meta__rating-count-number"
ID_END_OF_RESULTS   = "search-results__no-results_1-0"
CLASS_INGREDIENT    = "mntl-structured-ingredients__list-item"
ID_RECIPE_RATING    = "mntl-recipe-review-bar__rating_2-0"
TAG_INGR_QUANTITY   = "data-ingredient-quantity"
TAG_INGR_UNIT       = "data-ingredient-unit"
TAG_INGR_NAME       = "data-ingredient-name"

#Dictionary to store ingredients and quantities  
ingredients = {}

def search(query):

    offset = 0
    recipes = []
    endOfResults = False
    query = query.replace(" ","+")

    #Cycle through pages of results storing recipe html until end of results is reached.
    while(not endOfResults):

        search_url = "https://www.allrecipes.com/search?"+query+"="+query+"&offset="+str(offset)+"&q="+query

        # Accessing webpage
        site = urlopen(search_url)
        page_html = site.read()
        site.close()

        # Using beautiful soup to isolate individual recipe links. 
        page_s = Soup(page_html, "html.parser")
        results_s = page_s.findAll("a",{"class":CLASS_RECIPE_CARD})
 
        for result in results_s:
            if isRecipe(result):
                recipes.append(result["href"])

        endOfResults = isEndOfResults(page_s)
        
        #Incrementing offset by page size to reach next page of results. 
        offset += RESULT_OFFSET_SIZE
    
    return recipes
    
#Checks for html to differentiate recipes from articles/lists    
def isRecipe(result):
    return not result.find("div",{"class":CLASS_RECIPE_RATING}) == None

#Checks for html indicating a lack of results. 
def isEndOfResults(page_s):
    return not page_s.find("div",{"id":ID_END_OF_RESULTS}) == None

#Gather recipe html from a list of urls 
def getRecipes(urls):
    
    recipes = []

    for url in urls:
        # Accessing webpage and storing html
        site = urlopen(url)
        page_html = site.read()
        site.close()
        recipes.append(Soup(page_html,"html.parser"))

    return recipes

# Extract ingredients from the recepies and store in tuples of (quantity, unit of measure, name).
def extractIngredients(recipe_s):
    ingredients = []
    ingredients_s = recipe_s.findAll("li",{"class":CLASS_INGREDIENT})
    
    for ing_s in ingredients_s:

        try:
            quantity = ing_s.find("span",{TAG_INGR_QUANTITY:"true"}).string
        except:
            quantity = None
        try:
            unit = ing_s.find("span",{TAG_INGR_UNIT:"true"}).string
        except:
            unit = None
        try:
            name = ing_s.find("span",{TAG_INGR_NAME:"true"}).string
        except:
            name = None

        ingredients.append((quantity, unit, name))
    
    return ingredients

'''
def extractSteps(recipe_s):
   return False 
'''

def getRating(recipe_s):
    return float(recipe_s.find("div",{"id":ID_RECIPE_RATING}).string)

def catagorizeIngredients(ingList, rating):

    for curIng in ingList:
        for ing in ingredients:
            if jellyfish.jaro_similarity(curIng[1].lower(),ing.lower()) > ING_SIM_ALLOWANCE:
                ingredients[ing] += curIng[0]*rating
                return 
    ingredients[curIng[1]] = curIng[0]*rating  

def convertIngQuantity(ingList):
    units = {"cup":250,"c":250,
             "gram":1,"g":1,
             "millilitre":1,"ml":1,
             "milligram":1/1000,"mg":1/1000,
             "litre":1000, "l":1000,
             "tablespoon":15,"tbsp":15,
             "teaspoon":5,"tsp":5}
    #for ing in ingList:


def strToNum(string):
    fracDict = {"½":1/2,"⅓":1/3,"⅔":2/3,"¼":1/4,"¾":3/4,"⅛":1/8,"⅜":3/8,"⅝":5/8,"⅞":7/8}
    
    try:
        return eval(string)
    except: 
        try:
            lst = string.spit(" ")
            sum = 0
            for i in lst:
                try:
                    sum += eval(string)
                except: 
                    sum += fracDict[string]

            return sum
            
        except:
            return None

#RUNNER SECTION
start = time.time()
recipeURLs = search("sushi")
recipes = getRecipes(recipeURLs)

for recipe in recipes:
    print(str(getRating(recipe)) + " - " + str(extractIngredients(recipe)))

end = time.time()
print("Time: " + str(end-start))
print("Recipes collected: "  + str(len(recipes)))

