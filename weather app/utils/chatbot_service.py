"""
Chatbot Service
Handles FAQ-based chatbot using Google Gemini API
"""

import os
import json
import google.generativeai as genai
from typing import Dict, List, Optional

class ChatbotService:
    """
    Simple FAQ-based chatbot service using Google Gemini API
    """
    
    _instance = None
    _client = None
    _faqs = []
    _faq_context = ""
    
    def __new__(cls):
        """Singleton pattern to avoid reloading FAQs"""
        if cls._instance is None:
            cls._instance = super(ChatbotService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the chatbot service"""
        try:
            # Load Gemini API key
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                print("⚠️ WARNING: GEMINI_API_KEY not found in environment variables")
                self._client = None
                return
            
            # Initialize Gemini
            genai.configure(api_key=api_key)
            
            # Use Gemini 2.5 Flash model (latest and fastest free tier model)
            self._client = genai.GenerativeModel('gemini-2.5-flash')
            
            # Load FAQs
            self._load_faqs()
            
            print(f"✅ Chatbot Service initialized with {len(self._faqs)} FAQs using Gemini 2.5 Flash")
            
        except Exception as e:
            print(f"❌ Error initializing Chatbot Service: {str(e)}")
            self._client = None
    
    def _load_faqs(self):
        """Load FAQs from JSON file"""
        try:
            # Get the path to faqs.json
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            faq_path = os.path.join(current_dir, 'data', 'faqs.json')
            
            # Load FAQs
            with open(faq_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._faqs = data.get('faqs', [])
            
            # Create FAQ context string for ChatGPT
            self._faq_context = self._create_faq_context()
            
        except FileNotFoundError:
            print("⚠️ WARNING: faqs.json file not found")
            self._faqs = []
            self._faq_context = ""
        except json.JSONDecodeError as e:
            print(f"⚠️ WARNING: Error parsing faqs.json: {str(e)}")
            self._faqs = []
            self._faq_context = ""
        except Exception as e:
            print(f"⚠️ WARNING: Error loading FAQs: {str(e)}")
            self._faqs = []
            self._faq_context = ""
    
    def _create_faq_context(self) -> str:
        """Create a formatted FAQ context string for ChatGPT"""
        if not self._faqs:
            return ""
        
        context_parts = ["Here are the FAQs about Trip Planner:\n"]
        
        for idx, faq in enumerate(self._faqs, 1):
            question = faq.get('question', '')
            answer = faq.get('answer', '')
            context_parts.append(f"\nQ{idx}: {question}")
            context_parts.append(f"A{idx}: {answer}")
        
        return "\n".join(context_parts)
    
    def is_available(self) -> bool:
        """Check if chatbot service is available"""
        return self._client is not None and len(self._faqs) > 0
    
    def get_faq_count(self) -> int:
        """Get number of loaded FAQs"""
        return len(self._faqs)
    
    def ask(self, question: str, user_context: Optional[Dict] = None) -> Dict:
        """
        Ask a question to the chatbot using Gemini
        
        Args:
            question: User's question
            user_context: Optional context about the user (username, trip info, etc.)
        
        Returns:
            Dictionary with answer and metadata
        """
        try:
            # Check if service is available
            if not self.is_available():
                return {
                    'success': False,
                    'error': 'Chatbot service is not available. Please check API key and FAQ data.',
                    'answer': None
                }
            
            # Validate question
            if not question or not question.strip():
                return {
                    'success': False,
                    'error': 'Question cannot be empty',
                    'answer': None
                }
            
            # Prepare prompt with FAQ context
            prompt = self._create_prompt(question, user_context)
            
            # Call Gemini 2.5 Flash API with optimized config
            response = self._client.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    top_p=0.9,
                    top_k=40,
                    max_output_tokens=300,
                )
            )
            
            # Extract answer
            answer = response.text.strip()
            
            return {
                'success': True,
                'answer': answer,
                'question': question,
                'model': 'gemini-2.5-flash',
                'tokens_used': None  # Gemini doesn't return token count directly
            }
            
        except Exception as e:
            print(f"❌ Chatbot error: {str(e)}")
            return {
                'success': False,
                'error': f'Error processing your question: {str(e)}',
                'answer': None
            }
    
    def _create_prompt(self, question: str, user_context: Optional[Dict] = None) -> str:
        """
        Create prompt with FAQ context and instructions for Gemini
        
        Args:
            question: User's question
            user_context: Optional user context information
        
        Returns:
            Complete prompt string
        """
        base_prompt = """You are a helpful and friendly FAQ assistant for Trip Planner, a travel planning and expense tracking application.

Your role:
- Answer questions based ONLY on the provided FAQ information below
- Be concise and clear (keep answers under 150 words)
- Use a friendly, conversational tone
- Add relevant emojis to make responses engaging ✨
- If a question is not covered in the FAQs, politely say you don't have that information and suggest contacting support
- For step-by-step instructions, use numbered lists
- Emphasize key points using **bold** text

"""
        
        # Add user context if provided
        if user_context:
            username = user_context.get('username')
            if username:
                base_prompt += f"\nYou are currently helping user: {username}\n"
        
        # Add FAQ context
        base_prompt += f"\n{self._faq_context}\n"
        
        base_prompt += f"""\nRemember:
- Stay within the FAQ information provided
- Be helpful and encouraging
- Keep answers brief and actionable
- Use emojis appropriately 😊

User Question: {question}

Please provide a helpful answer based on the FAQ information above:"""
        
        return base_prompt
    
    def search_faqs(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Search FAQs by keyword (simple string matching)
        
        Args:
            query: Search query
            limit: Maximum number of results
        
        Returns:
            List of matching FAQ entries
        """
        if not query or not self._faqs:
            return []
        
        query_lower = query.lower()
        matches = []
        
        for faq in self._faqs:
            question = faq.get('question', '').lower()
            answer = faq.get('answer', '').lower()
            
            # Simple keyword matching
            if query_lower in question or query_lower in answer:
                matches.append({
                    'question': faq.get('question'),
                    'answer': faq.get('answer')
                })
                
                if len(matches) >= limit:
                    break
        
        return matches
    
    def get_all_faqs(self) -> List[Dict]:
        """Get all loaded FAQs"""
        return self._faqs.copy()
    
    def reload_faqs(self):
        """Reload FAQs from file (useful for updates)"""
        self._load_faqs()
        print(f"♻️ FAQs reloaded: {len(self._faqs)} entries")


# Create singleton instance
chatbot_service = ChatbotService()
