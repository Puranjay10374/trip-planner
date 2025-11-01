"""Service for fetching and processing weather data from WeatherAPI.com"""
import requests
from datetime import datetime, timedelta
from flask import current_app
import logging

logger = logging.getLogger(__name__)


class WeatherService:
    """Service for fetching and processing weather data"""
    
    @staticmethod
    def get_current_weather(destination):
        """
        Get current weather for a destination using WeatherAPI.com
        
        Args:
            destination (str): City name or "City, Country"
            
        Returns:
            dict: Weather data or error
        """
        try:
            api_key = current_app.config['WEATHER_API_KEY']
            base_url = current_app.config['WEATHER_API_BASE_URL']
            
            url = f"{base_url}/current.json"
            params = {
                'key': api_key,
                'q': destination,
                'aqi': 'no'  # Air quality index
            }
            
            logger.info(f"Fetching weather for: {destination}")
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 403:
                logger.error("Invalid API key")
                return {
                    'success': False,
                    'error': 'Invalid API key. Please check your WeatherAPI.com key.'
                }
            
            if response.status_code == 400:
                logger.error(f"Location not found: {destination}")
                return {
                    'success': False,
                    'error': f'Location "{destination}" not found. Please check the spelling or try "City, Country" format.'
                }
            
            response.raise_for_status()
            data = response.json()
            
            return {
                'success': True,
                'data': WeatherService._format_current_weather(data)
            }
            
        except requests.exceptions.Timeout:
            logger.error("Request timeout")
            return {
                'success': False,
                'error': 'Request timeout. Please try again.'
            }
        except requests.exceptions.ConnectionError:
            logger.error("Connection error")
            return {
                'success': False,
                'error': 'Unable to connect to weather service. Check your internet connection.'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Weather API error: {str(e)}")
            return {
                'success': False,
                'error': f'Weather API error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }
    
    @staticmethod
    def get_forecast(destination, days=5):
        """
        Get weather forecast for a destination using WeatherAPI.com
        
        Args:
            destination (str): City name or "City, Country"
            days (int): Number of days for forecast (max 5 for free API)
            
        Returns:
            dict: Forecast data or error
        """
        try:
            api_key = current_app.config['WEATHER_API_KEY']
            base_url = current_app.config['WEATHER_API_BASE_URL']
            
            # WeatherAPI.com free tier allows up to 14 days
            url = f"{base_url}/forecast.json"
            params = {
                'key': api_key,
                'q': destination,
                'days': min(days, 14),
                'aqi': 'no',
                'alerts': 'no'
            }
            
            logger.info(f"Fetching forecast for: {destination}")
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 403:
                return {
                    'success': False,
                    'error': 'Invalid API key'
                }
            
            if response.status_code == 400:
                return {
                    'success': False,
                    'error': f'Location "{destination}" not found'
                }
            
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'success': True,
                'data': WeatherService._format_forecast(data)
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Weather API error: {str(e)}")
            return {
                'success': False,
                'error': f'Unable to fetch forecast: {str(e)}'
            }
    
    @staticmethod
    def get_trip_weather(destination, start_date, end_date):
        """
        Get weather information for entire trip duration
        
        Args:
            destination (str): City name or "City, Country"
            start_date (date): Trip start date
            end_date (date): Trip end date
            
        Returns:
            dict: Weather data for trip duration
        """
        days_until_trip = (start_date - datetime.now().date()).days
        trip_duration = (end_date - start_date).days + 1
        
        result = {
            'destination': destination,
            'trip_start': start_date.isoformat(),
            'trip_end': end_date.isoformat(),
            'days_until_trip': days_until_trip,
            'trip_duration': trip_duration
        }
        
        # Get current weather
        current_weather = WeatherService.get_current_weather(destination)
        if current_weather['success']:
            result['current_weather'] = current_weather['data']
        else:
            result['current_weather_error'] = current_weather['error']
        
        # Get forecast if trip is within 5 days
        if days_until_trip <= 5 and days_until_trip >= 0:
            forecast = WeatherService.get_forecast(destination, min(trip_duration, 5))
            if forecast['success']:
                result['forecast'] = forecast['data']
                result['forecast_available'] = True
            else:
                result['forecast_error'] = forecast['error']
                result['forecast_available'] = False
        else:
            result['forecast_available'] = False
            if days_until_trip > 5:
                result['message'] = 'Forecast available up to 5 days in advance. Check back closer to your trip date.'
            else:
                result['message'] = 'Trip is in the past or starts today.'
        
        # Get historical average data
        result['historical_average'] = WeatherService._get_historical_average(start_date, end_date)
        
        # Weather recommendations
        if current_weather['success']:
            result['recommendations'] = WeatherService._generate_recommendations(
                current_weather['data']
            )
        
        return result
    
    @staticmethod
    def _format_current_weather(data):
        """Format current weather data from WeatherAPI.com"""
        location = data.get('location', {})
        current = data.get('current', {})
        condition = current.get('condition', {})
        
        return {
            'location': {
                'city': location.get('name'),
                'country': location.get('country'),
                'region': location.get('region'),
                'coordinates': {
                    'lat': location.get('lat'),
                    'lon': location.get('lon')
                },
                'timezone': location.get('tz_id'),
                'localtime': location.get('localtime')
            },
            'temperature': {
                'current': round(current.get('temp_c', 0), 1),
                'feels_like': round(current.get('feelslike_c', 0), 1),
                'unit': '°C'
            },
            'conditions': {
                'main': condition.get('text'),
                'description': condition.get('text'),
                'icon': condition.get('icon'),
                'icon_url': f"https:{condition.get('icon')}" if condition.get('icon') else None,
                'code': condition.get('code')
            },
            'wind': {
                'speed': current.get('wind_kph'),
                'direction': current.get('wind_dir'),
                'degree': current.get('wind_degree'),
                'unit': 'kph'
            },
            'humidity': current.get('humidity'),
            'pressure': current.get('pressure_mb'),
            'visibility': current.get('vis_km'),
            'clouds': current.get('cloud'),
            'uv_index': current.get('uv'),
            'last_updated': current.get('last_updated'),
            'is_day': current.get('is_day') == 1
        }
    
    @staticmethod
    def _format_forecast(data):
        """Format forecast data from WeatherAPI.com"""
        location = data.get('location', {})
        forecast_days = data.get('forecast', {}).get('forecastday', [])
        
        forecasts = []
        
        for day in forecast_days:
            date_str = day.get('date')
            date_obj = datetime.strptime(date_str, '%Y-%m-%d') if date_str else datetime.now()
            day_data = day.get('day', {})
            condition = day_data.get('condition', {})
            
            forecasts.append({
                'date': date_str,
                'day_name': date_obj.strftime('%A'),
                'temperature': {
                    'min': round(day_data.get('mintemp_c', 0), 1),
                    'max': round(day_data.get('maxtemp_c', 0), 1),
                    'avg': round(day_data.get('avgtemp_c', 0), 1),
                    'unit': '°C'
                },
                'conditions': {
                    'main': condition.get('text'),
                    'description': condition.get('text'),
                    'icon': condition.get('icon'),
                    'icon_url': f"https:{condition.get('icon')}" if condition.get('icon') else None,
                    'code': condition.get('code')
                },
                'humidity': {
                    'avg': day_data.get('avghumidity'),
                    'unit': '%'
                },
                'wind': {
                    'max_speed': day_data.get('maxwind_kph'),
                    'unit': 'kph'
                },
                'precipitation': {
                    'total_mm': day_data.get('totalprecip_mm', 0),
                    'total_snow_cm': day_data.get('totalsnow_cm', 0),
                    'chance_of_rain': day_data.get('daily_chance_of_rain', 0),
                    'chance_of_snow': day_data.get('daily_chance_of_snow', 0),
                    'unit': 'mm'
                },
                'uv_index': day_data.get('uv'),
                'sunrise': day.get('astro', {}).get('sunrise'),
                'sunset': day.get('astro', {}).get('sunset'),
                'moonrise': day.get('astro', {}).get('moonrise'),
                'moonset': day.get('astro', {}).get('moonset'),
                'moon_phase': day.get('astro', {}).get('moon_phase')
            })
        
        return {
            'location': {
                'city': location.get('name'),
                'country': location.get('country'),
                'region': location.get('region')
            },
            'daily_forecasts': forecasts
        }
    
    @staticmethod
    def _get_historical_average(start_date, end_date):
        """Get historical average weather data for the trip period"""
        month = start_date.month
        
        # Simple temperature averages by month (northern hemisphere - adjust based on location)
        temp_averages = {
            1: {'min': -2, 'max': 5, 'season': 'Winter'},
            2: {'min': 0, 'max': 7, 'season': 'Winter'},
            3: {'min': 3, 'max': 12, 'season': 'Spring'},
            4: {'min': 7, 'max': 16, 'season': 'Spring'},
            5: {'min': 11, 'max': 21, 'season': 'Spring'},
            6: {'min': 15, 'max': 25, 'season': 'Summer'},
            7: {'min': 17, 'max': 27, 'season': 'Summer'},
            8: {'min': 17, 'max': 27, 'season': 'Summer'},
            9: {'min': 13, 'max': 22, 'season': 'Fall'},
            10: {'min': 9, 'max': 16, 'season': 'Fall'},
            11: {'min': 4, 'max': 10, 'season': 'Fall'},
            12: {'min': 0, 'max': 6, 'season': 'Winter'}
        }
        
        return {
            'note': 'Historical averages based on seasonal patterns (Northern Hemisphere)',
            'season': temp_averages[month]['season'],
            'temperature': {
                'avg_min': temp_averages[month]['min'],
                'avg_max': temp_averages[month]['max'],
                'unit': '°C'
            }
        }
    
    @staticmethod
    def _generate_recommendations(weather_data):
        """Generate packing and activity recommendations based on weather"""
        recommendations = {
            'clothing': [],
            'activities': [],
            'precautions': []
        }
        
        if not weather_data:
            return recommendations
        
        temp = weather_data.get('temperature', {}).get('current', 20)
        conditions = weather_data.get('conditions', {}).get('main', '')
        
        # Temperature-based recommendations
        if temp < 0:
            recommendations['clothing'].extend([
                '🧥 Heavy winter coat',
                '🧤 Thermal underwear',
                '🧤 Gloves and warm hat',
                '🥾 Insulated boots'
            ])
            recommendations['activities'].append('⛷️ Indoor activities recommended due to extreme cold')
            recommendations['precautions'].append('❄️ Dress in layers to stay warm')
        elif temp < 10:
            recommendations['clothing'].extend([
                '🧥 Warm jacket',
                '👔 Sweater or hoodie',
                '👖 Long pants',
                '👟 Closed-toe shoes'
            ])
            recommendations['activities'].append('🚶 Good for walking tours with warm clothing')
        elif temp < 20:
            recommendations['clothing'].extend([
                '🧥 Light jacket or cardigan',
                '👕 Long sleeves recommended',
                '👟 Comfortable walking shoes'
            ])
            recommendations['activities'].append('🌤️ Perfect weather for sightseeing')
        else:
            recommendations['clothing'].extend([
                '👕 Light, breathable clothes',
                '🕶️ Sunglasses',
                '🧢 Sun hat or cap',
                '👡 Comfortable sandals/shoes'
            ])
            recommendations['activities'].append('☀️ Great weather for outdoor activities')
        
        # Condition-based recommendations
        if 'Rain' in conditions or 'Drizzle' in conditions:
            recommendations['clothing'].extend([
                '☔ Waterproof jacket or raincoat',
                '☂️ Umbrella',
                '🥾 Water-resistant shoes'
            ])
            recommendations['precautions'].append('🌧️ Plan for indoor alternatives')
            recommendations['activities'].append('🏛️ Visit museums and indoor attractions')
        
        if 'Snow' in conditions:
            recommendations['clothing'].extend([
                '🥾 Waterproof boots with good grip',
                '❄️ Snow gear and warm accessories'
            ])
            recommendations['precautions'].extend([
                '⚠️ Roads may be slippery - walk carefully',
                '❄️ Check for weather-related closures'
            ])
        
        if 'Clear' in conditions or 'Sunny' in conditions:
            if temp > 25:
                recommendations['clothing'].extend([
                    '🧴 Sunscreen (SPF 30+)',
                    '🕶️ UV protection sunglasses',
                    '💧 Water bottle'
                ])
                recommendations['precautions'].extend([
                    '💧 Stay hydrated - drink plenty of water',
                    '☀️ Avoid prolonged sun exposure during peak hours (11am-3pm)'
                ])
            recommendations['activities'].append('🏖️ Perfect for outdoor adventures and exploring')
        
        if 'Cloud' in conditions:
            recommendations['activities'].append('📸 Great lighting for photography')
        
        # Wind-based recommendations
        wind_speed = weather_data.get('wind', {}).get('speed', 0)
        if wind_speed > 10:
            recommendations['precautions'].append('💨 Windy conditions - secure loose items and hats')
            recommendations['clothing'].append('🧥 Windbreaker or wind-resistant jacket')
        
        # Humidity-based recommendations
        humidity = weather_data.get('humidity', 50)
        if humidity > 80:
            recommendations['precautions'].append('💦 High humidity - pack moisture-wicking clothes')
            recommendations['clothing'].append('👕 Breathable, quick-dry fabrics')
        
        if humidity < 30:
            recommendations['precautions'].append('💧 Low humidity - bring lip balm and moisturizer')
        
        return recommendations
