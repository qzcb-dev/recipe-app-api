from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient

from recipe.serializers import RecipeSerializer, RecipeDetailSerializer


RECIPE_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    """Return recipe detail url"""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def sample_tag(user, name='Main course'):
    """Create and return a sample tag"""
    return Tag.objects.create(user=user, name=name)


def sample_ingredient(user, name='Cinnamon'):
    """Create and return a sample ingredient"""
    return Ingredient.objects.create(user=user, name=name)


def sample_recipe(user, **params):
    """Create and return a sample recipe"""
    defaults = {
        'title': 'Sample recipe',
        'time_minutes': 10,
        'price': 5
    }
    defaults.update(params)

    return Recipe.objects.create(user=user, **defaults)


def create_user(**params):
    """Create and return a sample user"""
    return get_user_model().objects.create_user(
        email='test@test.com.py',
        password='testpass'
    )


class PublicRecipeApiTests(TestCase):
    """Test unauthenticated recipe API access"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """That that the authentication is required"""
        request = self.client.get(RECIPE_URL)

        self.assertEqual(request.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    """Test an authenticated recipe API access"""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """Test retrieve a list of recipies"""
        sample_recipe(user=self.user)
        sample_recipe(user=self.user)

        request = self.client.get(RECIPE_URL)

        recipies = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipies, many=True)

        self.assertEqual(request.status_code, status.HTTP_200_OK)
        self.assertEqual(request.data, serializer.data)

    def test_recipe_limited_to_user(self):
        """Test retrieving recipes for user"""
        user = get_user_model().objects.create_user(
            email='other@test.com.py',
            password='otherpass'
        )

        sample_recipe(user=user)
        sample_recipe(user=self.user)

        request = self.client.get(RECIPE_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(request.status_code, status.HTTP_200_OK)
        self.assertEqual(len(request.data), 1)
        self.assertEqual(request.data, serializer.data)

    def test_view_recipe_detail(self):
        """Test viewing a recipe detail"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        recipe.ingredient.add(sample_ingredient(user=self.user))

        url = detail_url(recipe.id)
        request = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)

        self.assertEqual(request.data, serializer.data)

    def test_create_basic_recipe(self):
        """Test creating recipe"""
        payload = {
            'title': 'Chocolate Cheesecake',
            'time_minutes': 30,
            'price': 5.00
        }
        request = self.client.post(RECIPE_URL, payload)

        self.assertEqual(request.status_code, status.HTTP_201_CREATED)

        recipe = Recipe.objects.get(id=request.data['id'])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))

    def test_create_recipe_with_tags(self):
        """Creating a recipe with tags"""
        tag1 = sample_tag(user=self.user, name='Vegan')
        tag2 = sample_tag(user=self.user, name='Dessert')
        payload = {
            'title': 'Avocado lime cheesecake',
            'tags': [tag1.id, tag2.id],
            'time_minutes': 60,
            'price': 20.00
        }

        request = self.client.post(RECIPE_URL, payload)

        self.assertEqual(request.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=request.data['id'])
        tags = recipe.tags.all()

        self.assertEqual(tags.count(), 2)
        self.assertIn(tag1, tags)
        self.assertIn(tag2, tags)

    def test_create_recipe_with_ingredients(self):
        """Test creating a recipe with ingredients"""
        ingredient1 = sample_ingredient(user=self.user, name="Prawns")
        ingredient2 = sample_ingredient(user=self.user, name="Ginger")
        payload = {
            'title': 'Thai prawn red curry',
            'ingredient': [ingredient1.id, ingredient2.id],
            'time_minutes': 20,
            'price': 7.00,
        }

        request = self.client.post(RECIPE_URL, payload)

        self.assertEqual(request.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=request.data['id'])
        ingredients = recipe.ingredient.all()

        self.assertEqual(ingredients.count(), 2)
        self.assertIn(ingredient1, ingredients)
        self.assertIn(ingredient2, ingredients)
