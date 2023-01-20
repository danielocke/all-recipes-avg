from urllib.request import urlopen
from bs4 import BeautifulSoup as Soup
import time
import jellyfish
import sys

#Number of recipes stored on each page of results by allrecipes website.
RESULT_OFFSET_SIZE = 24

#Allowed Jaro similarity between two strings for them to be considered the same ingredient/unit.
ING_SIM_ALLOWANCE = 0.5
UNIT_SIM_ALLOWANCE = 0.6
DUP_SIM_ALLOWANCE = 0.7

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

#Extracts rating from the html of a recipe page.
def getRating(recipe_s):
    return float(recipe_s.find("div",{"id":ID_RECIPE_RATING}).string)

#Places all (measure,ingredient) pairs into a dictionary with ingredients as keys.
def catagorizeIngredients(ingList, rating, destList):
    for curIng in ingList:

        matchFound = False

        if not "(optional)" in curIng[1].lower():
            if "," in curIng[1]:
                curIng = (curIng[0],(curIng[1].split(","))[0])
            if "(" in curIng[1] and ")" in curIng[1] and curIng[1].index("(") < curIng[1].index(")"):
                curIng = (curIng[0],(curIng[1][:curIng[1].index("(")] + curIng[1][curIng[1].index(")")+1:]))

            for ing in destList:
                if isSimilar(curIng[1].lower(),ing.lower(),ING_SIM_ALLOWANCE):
                    destList[ing] = maybeOp(destList[ing],maybeOp(curIng[0],rating,(lambda x,y: x*y)),(lambda x,y: x+y))
                    matchFound = True
                    break

            if not matchFound:
                destList[curIng[1]] = maybeOp(curIng[0],rating,(lambda x,y: x*y))

#Performs operation 'op' unless one or more of the operands has value 'None'.
def maybeOp(a,b,op):
    if not (a == None or b == None):
        return op(a,b)
    return None

#Converts measurement from allrecipes.com into a consistant numerical value.
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
            #print(str(ing[1]) + " : " + str(closest) + "\n")
            newIngList.append((float(ing[0])*units[closest],ing[2]))

        elif not ing[0] == None:
            noUnitList.append((float(ing[0]),ing[2]))
    
        else:
            noUnitList.append((None,ing[2]))

    return (newIngList,noUnitList)

#Conveting string numbers to floating point values.
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

#Identifies units that cannot be converted to numerical values. 
def isRejectUnit(unit):
    rejUnits = ["small","medium","large","pinch"]
    for rej in rejUnits:
        if rej in unit:
            return True
    return False

#Determines if two strings are similar within a given allowance.
def isSimilar(s1,s2,allow):
    if s1 in s2 or s2 in s1:
        return True
    elif jellyfish.jaro_similarity(s1,s2) > allow:
        return True

#Remove any dictionary entries from d2 if they appear in d1.
def removeDuplicates(d1,d2):
    newD2 = {}

    for i in d2: 
        newD2[i] = d2[i]

    for i in d2:
        for j in d1:
            if isSimilar(i,j,DUP_SIM_ALLOWANCE):
                del newD2[i]
                break
    return newD2

#Remove any ingredients from the dictionary if they have too small a quantity.
def removeOutliers(dict):
    sum = 0
    newDict = {}

    for i in dict: 
        newDict[i] = dict[i]

    for i in dict:
        if not dict[i] == None:
            sum += dict[i]
    for i in dict:
        if dict[i] < sum/100:
            del newDict[i]
    return newDict

#Converts all quantities in the dictionary to percentages of the total quantity.
def ratioToPercent(dict):
    sum = 0.0
    for i in dict:
        if not dict[i] == None:
            sum += dict[i]
    for i in dict:
        dict[i] = int((dict[i]/sum)*100)

#Displays the ingredient ratio.
def displayRatio(ing,nuIng,query):
    ing = dictToSrtLst(ing)

    print("Ratio of key ingredients in " + query + ":")
    for i in ing:
        print(str(i[1]) + "%:\t" + i[0])
    print("\nOther key ingredients in " + query + ":")
    for i in nuIng:
        print(i)

#Converts dictionary to sorted list.
def dictToSrtLst(d):
    l = []

    for ing in d:       
        l.append((ing,d[ing]))
    
    l = quicksort(l)

    return l
    
#Quicksort for list of (ingredient,quantity) pairs. 
def quicksort(l):
    n = len(l)

    if n <= 1:
        return l
    
    k = l[0]
    l = l[1:]

    h,t = 0,len(l)-1

    while h < t:
        if not l[h][1] > k[1]:
            h = h + 1
        if not l[t][1] < k[1]:
            t = t - 1
        if l[h][1] > k[1] and l[t][1] < k[1]:
            temp = l[h]
            l[h] = l[t]
            l[t] = temp
    if h > t:
        return quicksort(l[:h]) + [k] + quicksort(l[h:])
    elif l[h][1] < k[1]:
        return quicksort(l[:h]) + [l[h],k] + quicksort(l[h+1:])
    else:
        return quicksort(l[:h]) + [k,l[h]] + quicksort(l[h+1:])

#Determine ratios of key ingredients in the query recipe. 
def findAverageRatio(query):  
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
            pass
    
    noUnitIngredients = removeDuplicates(ingredients,noUnitIngredients)
    ingredients = removeOutliers(ingredients)
    ratioToPercent(ingredients)

    displayRatio(ingredients,noUnitIngredients,query)

#Run with argument from the command line. 
if __name__ == "__main__":
    query = str(sys.argv[1])
    findAverageRatio(query)
