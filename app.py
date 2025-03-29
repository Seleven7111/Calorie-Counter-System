from flask import Flask, render_template, request, jsonify
import sqlite3

app = Flask(__name__)
# 数据库连接
def get_db_connection():
    conn = sqlite3.connect('food_database.db')
    conn.row_factory = sqlite3.Row  # 使结果以字典形式返回
    return conn


@app.route('/')
def index():
    return render_template('index.html')
@app.route('/calculate')
def calculate():
    return render_template('calculator.html')
@app.route('/recipes')
def recipes():
    return render_template('recipes.html')

@app.route('/illness')
def searchRecipes():
    return render_template('indexillness.html')
@app.route('/random')
def searchRandom():
    return render_template('random.html')
@app.route('/searchFood', methods=['POST'])
def searchFood():
    name = request.form.get('name')
    conn = get_db_connection()
    cursor = conn.cursor()
    print(cursor)
    # 查询数据库
    cursor.execute("SELECT * FROM food_nutritional_facts WHERE Food_Name = ?", (name,))
    result = cursor.fetchone()
    print(f"Executing query: SELECT * FROM drinks WHERE name = '{name}'")

    conn.close()

    if result:
        return jsonify(dict(result))  # 将 Row 对象转换为字典
    else:
        return jsonify({"error": "Food is not found"})


@app.route('/randomFood', methods=['GET'])
def randomFood():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT Food_Name FROM food_nutritional_facts ORDER BY RANDOM() LIMIT 3")
    results = cursor.fetchall()
    foods = [row[0] for row in results]  # 提取食物名称
    conn.close()

    return jsonify({"random_foods": foods})
def calculate_bmr(gender, weight, height, age):
    if gender == 'male':
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    elif gender == 'female':
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    else:
        raise ValueError("Gender must be 'male' or 'female'")
    return round(bmr, 2)

# 插入用户信息到数据库
def insert_user_info(name, age, gender, height, weight, bmr):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_info (user_name, user_age, user_gender, user_height, user_weight, BMR)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, age, gender, height, weight, bmr))
    conn.commit()
    conn.close()

@app.route('/calculate_bmr', methods=['POST'])
def calculate_bmr_route():
    try:
        user_name = request.form.get('user_name')
        user_age = int(request.form.get('user_age'))
        user_gender = request.form.get('user_gender')
        user_height = float(request.form.get('user_height'))  # 身高单位：厘米
        user_weight = float(request.form.get('user_weight'))  # 体重单位：千克

        bmr = calculate_bmr(user_gender, user_weight, user_height, user_age)
        insert_user_info(user_name, user_age, user_gender, user_height, user_weight, bmr)

        response = {
            "message": f"Your daily minimum calories is: {bmr} Kcal.",
            "details": {
                "user_name": user_name,
                "age": user_age,
                "gender": user_gender,
                "height": user_height,
                "weight": user_weight,
                "bmr": bmr
            }
        }
        return jsonify(response)
    except ValueError as e:
        return jsonify({"error": str(e)})
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"})

# 获取食谱数量
def get_recipe_count(meal_type, ingredient_parts):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) AS total_amount
        FROM recipes
        WHERE RecipeID IN (
            SELECT RecipeID
            FROM recipes
            WHERE (Calories <= 500 AND ? = 'weight_loss')
               OR (Calories > 500 AND ? != 'weight_loss')
        ) AND RecipeIngredientParts LIKE ?
    ''', (meal_type, meal_type, f'%{ingredient_parts}%'))
    result = cursor.fetchone()
    conn.close()
    return result[0]

# 获取特定类型的食谱
def get_recipes_by_type_and_ingredient(meal_type, ingredient_parts):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT Name, Images, Calories, FatContent, CarbohydrateContent, ProteinContent, RecipeInstructions
        FROM recipes
        WHERE RecipeID IN (
            SELECT RecipeID
            FROM recipes
            WHERE (Calories <= 500 AND ? = 'weight_loss')
               OR (Calories > 500 AND ? != 'weight_loss')
        ) AND RecipeIngredientParts LIKE ?
    ''', (meal_type, meal_type, f'%{ingredient_parts}%'))
    recipes = cursor.fetchall()
    conn.close()
    return recipes

# 处理 RecipeInstructions，删除开头的 c( 和结尾的 )
def process_recipe_instructions(instructions):
    return instructions.replace("c(", "").replace(")", "")


@app.route('/get_recipes', methods=['POST'])
def get_recipes():
    try:
        meal_type = request.form.get('meal_type')
        ingredient_parts = request.form.get('ingredient_parts')
        total_amount = get_recipe_count(meal_type, ingredient_parts)
        recipes = get_recipes_by_type_and_ingredient(meal_type, ingredient_parts)

        response = {
            "total_amount": total_amount,
            "recipes": [
                {
                    "Name": recipe[0],
                    "Images": recipe[1],
                    "Calories": recipe[2],
                    "FatContent": recipe[3],
                    "CarbohydrateContent": recipe[4],
                    "Protein": recipe[5],
                    "RecipeInstructions": process_recipe_instructions(recipe[6])
                } for recipe in recipes
            ]
        }
        print(response)
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"})

@app.route('/get_illnesses', methods=['GET'])
def get_illnesses():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 查询所有不同的症状
    cursor.execute("SELECT DISTINCT Illness FROM nutrition_intake;")
    illnesses = cursor.fetchall()
    conn.close()

    return jsonify([illness['Illness'] for illness in illnesses])  # 返回症状列表

@app.route('/search', methods=['POST'])
def search():
    name = request.form.get('illness')
    conn = get_db_connection()
    cursor = conn.cursor()

    # query database
    cursor.execute("""SELECT food_category.Food_Name,FoodRecomandation,Category FROM nutrition_intake JOIN food_category on nutrition_intake.Category = food_category.Category_Name WHERE Illness = ? LIMIT 3;""", (name,))
    results = cursor.fetchall()
    conn.close()

    if results:
        # 将 Food_Name 提取并合并为一个字符串
        food_names = [row['Food_Name'] for row in results]
        food_names_str = ', '.join(food_names)  # 用逗号分隔
        food_recommendation = results[0]['FoodRecomandation']  # 假设使用第一个推荐
        category = results[0]['Category']  # 假设使用第一个类别

        return jsonify({
            'food_names': food_names_str,
            'food_recommendation': food_recommendation,
            'category': category
        })  # 返回合并的结果
    else:
        return jsonify({'error': 'No results found.'})  # 返回没有结果的提示



if __name__ == '__main__':
    app.run(debug=True,port=5003)