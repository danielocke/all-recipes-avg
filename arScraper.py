from urllib.request import urlopen
from bs4 import BeautifulSoup as Soup
import time
import jellyfish

#Number of recipes stored on each page of results by allrecipes website.
RESULT_OFFSET_SIZE = 24

#Allowed Jaro similarity between two strings for them to be considered the same ingredient/unit.
ING_SIM_ALLOWANCE = 0.15
UNIT_SIM_ALLOWANCE = 0.5

#HTML classes/id tags used by allRecipes
CLASS_RECIPE_CARD   = "comp mntl-card-list-items mntl-document-card mntl-card card card--no-image"
CLASS_RECIPE_RATING = "recipe-card-meta__rating-count-number"
ID_END_OF_RESULTS   = "search-results__no-results_1-0"
CLASS_INGREDIENT    = "mntl-structured-ingredients__list-item"
ID_RECIPE_RATING    = "mntl-recipe-review-bar__rating_2-0"
TAG_INGR_QUANTITY   = "data-ingredient-quantity"
TAG_INGR_UNIT       = "data-ingredient-unit"
TAG_INGR_NAME       = "data-ingredient-name"

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
            quantity = strToNum(ing_s.find("span",{TAG_INGR_QUANTITY:"true"}).string)
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

def catagorizeIngredients(ingList, rating, destList):
    for curIng in ingList:
        for ing in destList:
            if jellyfish.jaro_similarity(curIng[1].lower(),ing.lower()) > ING_SIM_ALLOWANCE:
                destList[ing] += curIng[0]*rating
                break
        destList[curIng[1]] = curIng[0]*rating  

def convertIngQuantity(ingList):
    newIngList = []
    noUnitList = []
    units = {"cup":250.0,
             "gram":1.0,"g":1.0,
             "millilitre":1.0,"ml":1.0,
             "milligram":1.0/1000.0,"mg":1.0/1000.0,
             "litre":1000.0, "l":1000.0,
             "tablespoon":15.0,"tbsp":15.0,
             "teaspoon":5,"tsp":5,
             "ounce":29,"oz":29,
             "clove":15}
    for ing in ingList:
        if not (ing[1] == None or ing[0] == None or isRejectUnit(ing[1])):
            closest = ""
            closestSim = 0.0
            for unit in units:
                curSim = jellyfish.jaro_similarity(ing[1],unit)
                if curSim > closestSim and curSim > UNIT_SIM_ALLOWANCE:
                    closest = unit
                    closestSim = curSim
            if closest == "":
                raise ValueError
            print(str(ing[1]) + " : " + str(closest) + "\n")
            newIngList.append((float(ing[0])*units[closest],ing[2]))

        elif not ing[0] == None:
            noUnitList.append((float(ing[0]),ing[2]))
    
        else:
            noUnitList.append((None,ing[2]))

    return (newIngList,noUnitList)

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

def isRejectUnit(unit):
    rejUnits = ["small","medium","large","pinch"]
    for rej in rejUnits:
        if unit.contains(rej):
            return True
    return False

def findAverageRatio(query):
    #Dictionary to store ingredients and quantities  
    ingredients = {}
    noUnitIngredients = {}

    recipeURLs = search(query)
    recipes = getRecipes(recipeURLs)

    for recipe in recipes:
        try:
            ingList = extractIngredients(recipe)
            rating = getRating(recipe)

            ingList = convertIngQuantity(ingList)

            catagorizeIngredients(ingList[0],rating,ingredients)
            catagorizeIngredients(ingList[1],rating,noUnitIngredients)
        except:
            print("ERROR")
    print("\nIngredients: " + str(ingredients))
    print("\nNU Ingredients: " + str(noUnitIngredients))

#RUNNER SECTION
start = time.time()
findAverageRatio("crab cake")
end = time.time()
print("Time: " + str(end-start))