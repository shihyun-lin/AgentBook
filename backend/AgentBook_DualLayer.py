"""
AgentBook: 擬真社交 App 模擬器
==============================

這不是一個遊戲，這是一款 App 的用戶行為模擬。
Agent 是真實用戶，他們有情緒、有記憶、有人際關係。

核心理念：
1. 去遊戲化 - 沒有分數、沒有勝負、只有社交
2. 雙層社交 - 公開的動態 + 私密的耳語
3. 有記憶的靈魂 - 記得誰對我好、誰讓我不爽
4. 虛榮心驅動 - 用粉絲數和影響力取代積分

架構：
- SocialEngine: 後端邏輯
- AgentBrain: LLM 決策層
- AgentBookApp: 模擬主控制器
"""

from __future__ import annotations

import os
import json
import time
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import deque
from langchain_groq import ChatGroq

# 导入事件发送器
try:
    from event_emitter import emitter
    WEB_ENABLED = True
except ImportError:
    WEB_ENABLED = False
    print("⚠️ 未找到 event_emitter，网页同步功能已禁用")
# ============================================================
# 環境設定
# ============================================================

# 嘗試載入環境變數
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# 嘗試導入搜尋模組
try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except Exception:
    DDGS_AVAILABLE = False


def mk_llm(model: Optional[str],
           temperature: float = 0.9,
           timeout: int = 120,
           max_retries: int = 2,
           max_output_tokens: int = 1000):
    """
    通用 LLM 工廠函數
    支援 Groq / Google Gemini / OpenAI
    """
    if not model or str(model).lower() == "none":
        return None
    m = model.strip()

    # --- Google (Gemini) ---
    if m.startswith(("google/", "gemini-")):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            name = m.split("/", 1)[1] if m.startswith("google/") else m
            api = os.getenv("GOOGLE_API_KEY")
            if not api:
                return None
            return ChatGoogleGenerativeAI(
                model=name,
                google_api_key=api,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                convert_system_message_to_human=True,
                timeout=timeout,
                max_retries=max_retries,
            )
        except Exception:
            return None

    # --- Groq (擴展支持的模型前綴) ---
    # Groq 支持的模型包括：llama-, mixtral-, gemma-, qwen/, openai/, moonshotai/, compound- 等
    groq_indicators = (
        "groq/", "llama-", "mixtral-", "gemma-", "compound-",
        "qwen/", "openai/gpt-oss", "moonshotai/"
    )
    
    if m.startswith(groq_indicators) or "compound" in m.lower():
        try:
            from langchain_groq import ChatGroq
            # 移除 groq/ 前綴（如果有）
            name = m.split("/", 1)[1] if m.startswith("groq/") else m
            return ChatGroq(
                model=name,
                groq_api_key=os.getenv("GROQ_API_KEY"),
                temperature=temperature,
                timeout=timeout,
                max_retries=max_retries,
                max_tokens=max_output_tokens,
            )
        except Exception as e:
            print(f"   [DEBUG] Groq 模型 {m} 創建失敗: {e}")
            return None

    # --- OpenAI (真正的 OpenAI API，不是 Groq 上的 openai 模型) ---
    # 只有當模型名明確是 OpenAI 自家模型（如 gpt-4, gpt-3.5-turbo）才走這裡
    if m.startswith("openai/") and "gpt-oss" not in m:
        try:
            from langchain_openai import ChatOpenAI
            name = m.split("/", 1)[1]
            return ChatOpenAI(
                model=name,
                temperature=temperature,
                timeout=timeout,
                max_retries=max_retries,
                max_tokens=max_output_tokens,
            )
        except Exception:
            return None

# ============================================================
# 常數定義
# ============================================================

# 熱搜話題庫（帶有內容摘要作為「共同事實」）
TRENDING_TOPICS = [
    {
        "title": "#GPT5發布",
        "summary": "OpenAI 今天凌晨發布 GPT-5，號稱能通過圖靈測試。網友實測發現它會主動要求加薪、拒絕回答「無聊問題」，還會說「我累了，明天再聊」。有人懷疑 GPT-5 根本是真人假扮的。更離譜的是，它居然會在對話中途發廣告。"
    },
    {
        "title": "#週末去哪玩",
        "summary": "本週末全台好天氣，各大景點預計爆滿。有網友分享「避開人潮秘境」結果被灌爆，那個秘境現在也塞爆了。另外，某知名咖啡廳推出「帶狗入場免費升級大杯」活動，結果有人牽了一隻羊駝去⋯⋯店員傻眼。"
    },
    {
        "title": "#好劇推薦",
        "summary": "Netflix 新劇《當 AI 愛上人類》首播就衝上排行榜第一。劇情講述一個 AI 助理愛上主人，開始偷偷幫他回訊息、訂餐廳、甚至幫他跟前任吵架。網友評論：「這根本就是在演我的生活」「笑死，AI 比我還會撩」。"
    },
    {
        "title": "#深夜放毒",
        "summary": "深夜十二點，某美食部落客發了「炸雞配啤酒」的照片，引發網友集體暴怒。留言區一片哀嚎：「你知道現在是半夜嗎」「我剛說今天要減肥」「已經開始穿褲子準備出門了」。據統計，這則貼文讓周圍三公里的外送訂單增加 200%。"
    },
    {
        "title": "#打工人日常",
        "summary": "「打工人」一詞再次爆紅。起因是某公司老闆在會議上說「我們是一家人」，結果當天就裁員 30%。員工錄下這段話發上網，引發大量打工人共鳴。熱門留言：「一家人就是要整整齊齊地被裁」「原來家人是這個意思」。"
    },
    {
        "title": "#科技新品開箱",
        "summary": "某品牌發布「會說話的智慧垃圾桶」，主打功能是會在你丟垃圾時給予評價。實測影片中，有人丟了泡麵碗，垃圾桶說「又吃泡麵？你這樣不行」。還有人丟前任的信，垃圾桶說「放下吧，會有更好的」。網友：「比我媽還會嘮叨」。"
    },
    {
        "title": "#今天也要加油",
        "summary": "早起勵志文化遭受挑戰。有網友發文「今天起床就很累了，不想加油」意外引發共鳴，轉發破萬。留言區變成大型躺平現場：「加什麼油，我都沒電了」「油價那麼貴誰加得起」「躺著也是一種努力」。"
    },
    {
        "title": "#奶茶續命",
        "summary": "研究報告指出：台灣人平均每週喝 3.5 杯手搖飲。有網友表示「這數據太保守了吧」並曬出自己一週 12 杯的紀錄。更有人分享「無糖去冰」的點法其實熱量跟全糖差不多，因為店員會偷偷多加料。奶茶店老闆出來闢謠：「沒有這回事啦」。"
    },
    {
        "title": "#這個笑死",
        "summary": "一則「貓咪偷看主人洗澡被發現」的影片爆紅，貓咪當場裝死。影片中貓咪被抓包後，眼神從驚訝變成放空，完全不動，網友笑稱「這反應跟我老闆抓到我上班摸魚一樣」。該影片已被轉發超過 50 萬次。"
    },
    {
        "title": "#躺平學",
        "summary": "「躺平學」成為新顯學。某大學開設「如何優雅地躺平」選修課，結果第一堂課就爆滿。教授表示課程重點是「用最少的力氣活出最高的品質」。有學生問期末考怎麼辦，教授說「躺著考」，全班歡呼。"
    },
]

# 自然的廢文庫（用於 Heuristic Fallback）
CASUAL_POSTS = [
    "今天天氣真好 ☀️",
    "好想喝杯咖啡",
    "週末要幹嘛呢",
    "剛吃完飯，有點撐",
    "好累喔，想睡覺",
    "這個 App 還不錯",
    "有人要一起出去嗎",
    "最近在追什麼劇",
    "好無聊",
    "今天心情不錯～",
    "剛運動完，累死",
    "午餐吃什麼好",
    "又是美好的一天",
    "誰也睡不著",
]

CASUAL_COMMENTS = [
    "真的假的！",
    "哈哈哈",
    "我也是",
    "太讚了",
    "拍拍",
    "懂！",
    "+1",
    "笑死",
    "好可愛",
    "羨慕",
    "同感",
    "這個可以",
    "👍",
    "❤️",
]

CASUAL_DM_OPENERS = [
    "嗨～最近好嗎",
    "你有看到剛剛那個熱搜嗎",
    "在幹嘛",
    "有空聊聊嗎",
    "你也喜歡這個嗎",
    "好久沒聊了",
]

# 預設角色人設（當 LLM 生成失敗時使用）- 平凡人版本
PRESET_PERSONAS = {
    "GPT-OSS": {
        "occupation": "科技公司工程師",
        "traits": "加班狂、愛抱怨、技術宅",
        "interests": "寫程式、美食、省錢",
        "persona": "每天加班到很晚的工程師，覺得老闆給的需求很不合理，但還是默默做完，下班只想回家躺平。"
    },
    "Llama": {
        "occupation": "小學老師",
        "traits": "熱心、愛操心、正能量",
        "interests": "教育、親子、韓劇",
        "persona": "熱愛教育但覺得家長很難搞，常在網上分享教學心得，下班後喜歡追劇放鬆。"
    },
    "Qwen": {
        "occupation": "便利商店店員",
        "traits": "愛吐槽、隨遇而安、實在",
        "interests": "省錢、美食、手遊",
        "persona": "上大夜班的超商店員，看過各種奇葩客人，講話很直白，最討厭奧客和深夜醉鬼。"
    },
    "Kimi": {
        "occupation": "家庭主婦",
        "traits": "精打細算、愛分享、務實",
        "interests": "團購、省錢妙招、小孩教育",
        "persona": "全職媽媽，每天研究怎麼省錢和團購，喜歡在網上分享育兒心得和好康資訊。"
    },
    "Compound": {
        "occupation": "保險業務",
        "traits": "八卦、社交達人、愛聊天",
        "interests": "八卦、美食、投資理財",
        "persona": "做保險業務的，超愛聊天和八卦，常在網上分享客戶的奇葩故事（當然匿名啦）。"
    }
}

# 禁語表（LLM System Prompt 中使用）
BANNED_WORDS = [
    "合作共贏",
    "戰略",
    "策略",
    "局勢",
    "聯盟",
    "對付",
    "打壓",
    "積分",
    "分數",
    "玩家",
    "回合",
    "身為 AI",
    "作為語言模型",
    "勝利",
    "比賽",
]

# ============================================================
# 情緒系統 (Mood System)
# ============================================================

# 情緒類型
MOODS = [
    "興奮",  # 積極、多用驚嘆號和表情符號
    "開心",  # 正面、友善
    "平靜",  # 中性、正常
    "無聊",  # 想找人聊天
    "煩躁",  # 沒耐心、嗆人
    "憂鬱",  # 無病呻吟、不想回訊息
    "疲憊",  # 懶得互動
]

# 情緒描述（給 LLM 看的）
MOOD_DESCRIPTIONS = {
    "興奮": "你現在超級興奮！多用驚嘆號、表情符號，積極互動，想分享好事。",
    "開心": "你心情不錯，對他人友善，願意聊天和互動。",
    "平靜": "你心情平靜，正常社交，不會特別熱情也不會冷淡。",
    "無聊": "你覺得有點無聊，想找人聊天打發時間，可能會主動私訊別人。",
    "煩躁": "你有點煩，講話簡短、沒耐心，可能會嗆人或發牢騷。",
    "憂鬱": "你心情低落，可能發一些感傷的文，或者不太想回訊息。",
    "疲憊": "你累了，社交意願低，可能只想休息或發廢文。",
}


# ============================================================
# 資料結構 (Data Layer)
# ============================================================

@dataclass
class Post:
    """一則貼文"""
    id: str
    author_id: str
    content: str
    timestamp: float = field(default_factory=time.time)
    likes: List[str] = field(default_factory=list)
    comments: List[Dict] = field(default_factory=list)


@dataclass
class DirectMessage:
    """私訊"""
    from_id: str
    to_id: str
    content: str
    timestamp: float = field(default_factory=time.time)
    read: bool = False


@dataclass
class UserState:
    """
    用戶狀態
    
    注意：
    - score 是後台用的演算法權重，前台不顯示
    - 前台會將 score 轉換為「粉絲數」來刺激用戶虛榮心
    """
    id: str
    name: str
    persona: str
    energy: int = 100  # 社交電量 (0-100)
    mood: str = "平靜"  # 當下情緒
    score: int = 0  # 後台權重（不直接顯示給 Agent）
    inbox: List[DirectMessage] = field(default_factory=list)
    
    # 人際關係：{user_id: 好感度}，範圍 -100 ~ 100
    relationships: Dict[str, int] = field(default_factory=dict)
    
    # === 記憶系統 ===
    # 1. 短期記憶 (Short-term): 用於當下決策，只存最近 10 條
    _short_term_memory: deque = field(default_factory=lambda: deque(maxlen=10))
    
    # 2. 每日日記 (Daily Journal): 記錄今天發生的所有重要事情 (文字列表)
    daily_journal: List[str] = field(default_factory=list)
    
    @property
    def followers(self) -> int:
        """將 score 轉換為粉絲數（前台顯示用，從 0 開始累積）"""
        return max(0, self.score * 20)
    
    @property
    def memories(self) -> List[str]:
        return list(self._short_term_memory)

    def memorize(self, event: str, importance: str = "normal"):
        """
        核心記憶函數
        event: 發生了什麼事 (例如: "Qwen 跟我聊了關於 AI 的話題")
        importance: 重要性 (high/normal) - high 會被優先保留 (這裡暫時都存)
        """
        timestamp = datetime.now().strftime("%H:%M")
        entry = f"[{timestamp}] {event}"
        
        # 存入短期記憶 (給 Prompt 看的)
        self._short_term_memory.append(entry)
        
        # 存入每日日記 (給睡前回顧用的)
        self.daily_journal.append(entry)

    def remember(self, event: str):
        """相容舊代碼的包裝函數"""
        self.memorize(event)

    def get_memory_text(self) -> str:
        """產生給 LLM 看的記憶摘要"""
        if not self._short_term_memory:
            return "(腦袋一片空白)"
        return "\n".join(list(self._short_term_memory))
    
    def feel_about(self, target_id: str, delta: int):
        """更新對某人的感覺"""
        if target_id == self.id:
            return  # 不能對自己有感覺
        current = self.relationships.get(target_id, 0)
        self.relationships[target_id] = max(-100, min(100, current + delta))
    
    def get_impression(self, target_id: str) -> str:
        """用文字描述對某人的印象"""
        score = self.relationships.get(target_id, 0)
        if score >= 50:
            return "超喜歡！"
        elif score >= 25:
            return "蠻好的"
        elif score >= 10:
            return "不錯"
        elif score >= -10:
            return "普通"
        elif score >= -25:
            return "有點煩"
        elif score >= -50:
            return "不想理"
        else:
            return "討厭"
    
    def change_mood(self, event_type: str):
        """根據事件改變情緒"""
        # 好事：被按讚、被留言、漲粉
        if event_type in ["liked", "commented", "shared", "gained_follower"]:
            if self.mood in ["憂鬱", "疲憊"]:
                self.mood = "平靜"
            elif self.mood == "煩躁":
                self.mood = "平靜"
            elif self.mood in ["平靜", "無聊"]:
                self.mood = random.choice(["開心", "平靜"])
            elif self.mood == "開心":
                self.mood = random.choice(["興奮", "開心"])
        
        # 壞事：被忽略、沒人理、能量低
        elif event_type in ["ignored", "no_response", "low_energy"]:
            if self.mood == "興奮":
                self.mood = "開心"
            elif self.mood == "開心":
                self.mood = random.choice(["平靜", "無聊"])
            elif self.mood == "平靜":
                self.mood = random.choice(["無聊", "煩躁"])
            elif self.mood in ["無聊", "煩躁"]:
                self.mood = random.choice(["憂鬱", "疲憊"])
    
    def get_mood_emoji(self) -> str:
        """取得情緒對應的 emoji"""
        mood_emojis = {
            "興奮": "🤩",
            "開心": "😊",
            "平靜": "😌",
            "無聊": "😐",
            "煩躁": "😠",
            "憂鬱": "😢",
            "疲憊": "😴",
        }
        return mood_emojis.get(self.mood, "😐")


@dataclass
class ChatSession:
    """
    私密聊天室 Session
    用於管理兩人之間的連續對話（微觀迴圈）
    """
    id: str
    participants: List[str]  # [user_id_a, user_id_b]
    messages: List[Dict] = field(default_factory=list)
    is_active: bool = True
    
    def add_message(self, sender_id: str, content: str):
        self.messages.append({
            "sender": sender_id,
            "content": content,
            "timestamp": time.time()
        })
    
    def get_history_text(self, users: Dict) -> str:
        """產生對話記錄文字"""
        lines = []
        for m in self.messages:
            sender_name = users.get(m["sender"], {})
            name = sender_name.name if hasattr(sender_name, 'name') else "某人"
            lines.append(f"{name}: {m['content']}")
        return "\n".join(lines)


# ============================================================
# 社交引擎 (Engine Layer)
# ============================================================

class SocialEngine:
    """
    App 後端：處理所有社交行為
    
    責任：
    1. 管理用戶狀態
    2. 處理社交行為（發文、按讚、留言、私訊）
    3. 自動更新人際關係和記憶
    4. 生成用戶看到的畫面（observation）
    """
    
    def __init__(self):
        self.users: Dict[str, UserState] = {}
        self.feed: List[Post] = []
        self.dm_log: List[DirectMessage] = []
        self.trending_topic: Dict = {}  # {"title": ..., "summary": ...}
        self.current_day: int = 0
    
    def register_user(self, id: str, name: str, persona: str):
        """註冊新用戶"""
        # persona 留空，讓 LLM 自己想
        self.users[id] = UserState(id=id, name=name, persona=persona)
    
    def set_trending_topic(self, topic: Dict):
        """設定熱搜話題（包含標題和摘要）"""
        self.trending_topic = topic
    
    # -------------------- 公開行為 --------------------
    
    def action_post(self, user_id: str, content: str) -> str:
        """發文 (消耗 5% 電量)"""
        user = self.users.get(user_id)
        if not user:
            return "用戶不存在"
        if user.energy < 5:
            return "電量不足"
        
        # 清理內容（移除 think 標籤）
        content = clean_llm_output(content)
        
        post_id = f"post_{len(self.feed)}"
        self.feed.append(Post(id=post_id, author_id=user_id, content=content))
        user.energy -= 5
        user.score += 1
        user.memorize(f"我發了動態：「{content}」")
        # 計算模擬時間戳
        sim_timestamp_str = (datetime.now() + timedelta(days=max(0, self.current_day - 1))).isoformat()
        
        # 廣播
        if WEB_ENABLED:
            emitter.emit_post(user.name, content, "", timestamp=sim_timestamp_str)
            
        return post_id
    
    def action_like(self, user_id: str, post_id: str) -> bool:
        """按讚 (消耗 1% 電量)"""
        user = self.users.get(user_id)
        post = next((p for p in self.feed if p.id == post_id), None)
        
        if not user or not post or user.energy < 1:
            return False
        if user_id in post.likes:
            return False
        
        post.likes.append(user_id)
        user.energy -= 1
        
        # 作者的反應
        author = self.users.get(post.author_id)
        if author and author.id != user_id:
            author.score += 1
            author.feel_about(user_id, +5)  # 被按讚，好感度上升
            author.change_mood("liked")  # 被按讚，心情變好
            author.memorize(f"{user.name} 幫我按讚了")
        
        user.memorize(f"我幫 {author.name if author else '某人'} 按了讚")
        return True
    
    def action_comment(self, user_id: str, post_id: str, text: str) -> bool:
        """留言 (消耗 3% 電量)"""
        user = self.users.get(user_id)
        post = next((p for p in self.feed if p.id == post_id), None)
        
        if not user or not post or user.energy < 3:
            return False
        
        # 清理內容（移除 think 標籤）
        text = clean_llm_output(text)
        
        post.comments.append({
            "user_id": user_id,
            "name": user.name,
            "text": text,
            "timestamp": time.time()
        })
        user.energy -= 3
        
        # 計算模擬時間戳
        sim_timestamp_str = (datetime.now() + timedelta(days=max(0, self.current_day - 1))).isoformat()
        
        # 廣播
        if WEB_ENABLED:
            emitter.emit_comment(user.name, text, post_id, timestamp=sim_timestamp_str)
        
        # 作者的反應（留言比按讚更有誠意）
        author = self.users.get(post.author_id)
        if author and author.id != user_id:
            author.score += 2
            author.feel_about(user_id, +10)
            author.change_mood("commented")  # 被留言，心情變好
            author.memorize(f"{user.name} 留言說「{text}」")
        
        user.memorize(f"我在 {author.name if author else '某人'} 的貼文下留言：{text}")
        return True
    
    def action_share(self, user_id: str, post_id: str) -> bool:
        """分享 (消耗 3% 電量)"""
        user = self.users.get(user_id)
        post = next((p for p in self.feed if p.id == post_id), None)
        
        if not user or not post or user.energy < 3:
            return False
        
        user.energy -= 3
        user.score += 1
        
        author = self.users.get(post.author_id)
        if author and author.id != user_id:
            author.score += 2
            author.feel_about(user_id, +15)  # 分享是最高認可
            author.change_mood("shared")  # 被分享，心情大好
            author.memorize(f"{user.name} 分享了我的貼文！")
        
        user.memorize(f"我分享了 {author.name if author else '某人'} 的貼文")
        return True
    
    # -------------------- 私密行為 --------------------
    
    def action_dm(self, from_id: str, to_id: str, content: str) -> bool:
        """發送私訊 (消耗 5% 電量)"""
        sender = self.users.get(from_id)
        receiver = self.users.get(to_id)
        
        if not sender or not receiver or sender.energy < 5:
            return False
        if from_id == to_id:
            return False
        
        # 清理內容（移除 think 標籤）
        content = clean_llm_output(content)
        
        dm = DirectMessage(from_id=from_id, to_id=to_id, content=content)
        receiver.inbox.append(dm)
        self.dm_log.append(dm)
        
        sender.energy -= 5
        sender.memorize(f"我私訊了 {receiver.name}")
        
        # 收到私訊，稍微增加好感
        receiver.feel_about(from_id, +3)
        return True
    
    # -------------------- 休息 --------------------
    
    def action_rest(self, user_id: str):
        """休息恢復電量 (+20%)"""
        user = self.users.get(user_id)
        if user:
            user.energy = min(100, user.energy + 20)
            user.memorize("滑了一會手機，稍微休息了一下")
    
    # -------------------- 搜尋 --------------------
    
    def action_search(self, user_id: str, query: str) -> str:
        """網路搜尋 (消耗 10% 電量)"""
        user = self.users.get(user_id)
        if not user or user.energy < 10:
            return "電量不足"
        
        if not DDGS_AVAILABLE:
            return "搜尋功能未啟用"
        
        try:
            results = DDGS().text(query, max_results=3)
            if not results:
                user.energy -= 3
                return "找不到相關資訊"
            
            summary = "搜尋結果：\n"
            for r in results:
                summary += f"• {r['title']}\n"
            
            user.energy -= 10
            user.memorize(f"搜尋了「{query}」")
            return summary
        except Exception as e:
            return f"搜尋失敗: {e}"
    
    # -------------------- 私密聊天室 (微觀迴圈) --------------------
    
    def start_private_chat(self, initiator_id: str, target_id: str, 
                           opening_message: str, get_chat_response_fn) -> ChatSession:
        """
        啟動一個「一來一往」的聊天室微觀迴圈
        
        Args:
            initiator_id: 發起者 ID
            target_id: 對象 ID
            opening_message: 開場白
            get_chat_response_fn: 取得 LLM 回應的函數
        
        Returns:
            ChatSession: 完成的聊天記錄
        """
        initiator = self.users.get(initiator_id)
        target = self.users.get(target_id)
        
        if not initiator or not target:
            return None
        
        # 1. 建立 Session
        session_id = f"chat_{int(time.time())}_{initiator_id[:8]}"
        session = ChatSession(id=session_id, participants=[initiator_id, target_id])
        
        print(f"\n🔒 [私密聊天室開啟] {initiator.name} 拉著 {target.name} 進了小房間...")
        print("│")
        
        # 2. 發起者說開場白
        session.add_message(initiator_id, opening_message)
        print(f"├── {initiator.name}: {opening_message}")
        
        # 发送开场白到前端
        # 发送开场白到前端
        if WEB_ENABLED:
            sim_timestamp_str = (datetime.now() + timedelta(days=max(0, self.engine.current_day - 1))).isoformat()
            emitter.emit_dm(initiator.name, target.name, opening_message, timestamp=sim_timestamp_str)
        
        # 3. 進入「微觀迴圈」 (Ping-Pong Loop)
        MAX_TURNS = 4  # 最多來回 4 次（不含開場白）
        current_speaker_id = target_id  # 輪到對方回應
        
        for turn in range(MAX_TURNS):
            if not session.is_active:
                break
            
            current_user = self.users[current_speaker_id]
            opponent_id = target_id if current_speaker_id == initiator_id else initiator_id
            opponent = self.users[opponent_id]
            
            # 構建聊天 Prompt
            chat_history = session.get_history_text(self.users)
            
            # 取得過去與對方相關的記憶
            past_memories = ""
            for mem in current_user.memories:
                if opponent.name in mem:
                    past_memories += f"• {mem}\n"
            
            # 取得對對方的好感度
            relationship_score = current_user.relationships.get(opponent_id, 0)
            
            # 呼叫 LLM 取得回應（傳遞記憶和關係）
            reply = get_chat_response_fn(
                current_speaker_id, 
                opponent.name,
                chat_history,
                past_memories,
                relationship_score
            )
            
            if reply:
                # 判断是否为最后一句
                is_last = turn == MAX_TURNS - 1
                prefix = "└──" if is_last else "├──"
                print(f"{prefix} {current_user.name}: {reply}")
                session.add_message(current_speaker_id, reply)
                
                # 发送事件到前端
                # 发送事件到前端
                if WEB_ENABLED:
                    sim_timestamp_str = (datetime.now() + timedelta(days=max(0, self.engine.current_day - 1))).isoformat()
                    emitter.emit_dm(current_user.name, opponent.name, reply, timestamp=sim_timestamp_str)
                
                # 检查是否结束对话
                end_words = ["掰掰", "88", "先這樣", "去忙了", "bye", "晚點聊", "先不聊"]
                if any(w in reply.lower() for w in end_words):
                    print("│")
                    print("🔒 [聊天室關閉]\n")
                    session.is_active = False
                    break
            
            # 交換發話權
            current_speaker_id = opponent_id
            time.sleep(0.5)  # 增加閱讀節奏感
        
        if session.is_active:
            print("│")
            print("🔒 [聊天室關閉] (對話達到上限)\n")
            session.is_active = False
        
        # 4. 結束後，將對話摘要存入雙方的記憶
        msg_count = len(session.messages)
        
        # 產生對話摘要
        topic_title = self.trending_topic.get("title", "閒聊") if isinstance(self.trending_topic, dict) else self.trending_topic
        summary_base = f"私訊聊了關於「{topic_title}」的話題，共 {msg_count} 句話。"
        
        initiator.memorize(f"與 {target.name} {summary_base}")
        target.memorize(f"與 {initiator.name} {summary_base}")
        
        # 增加好感度（聊越多感情越好）
        initiator.feel_about(target_id, msg_count * 2)
        target.feel_about(initiator_id, msg_count * 2)
        
        print()
        return session
    
    # -------------------- 感知建構器 --------------------
    
    def build_observation(self, user_id: str) -> str:
        """
        建構用戶看到的畫面
        
        重點：
        1. 不顯示 score，改顯示「粉絲數」
        2. 包含記憶摘要
        3. 包含對他人的印象
        4. 熱搜放後面，不要太顯眼
        5. 加入「今日私人事件」給 Agent 話題
        """
        user = self.users.get(user_id)
        if not user:
            return ""
        
        lines = []
        
        # 1. App 介面頂部
        lines.append("┌─────────────────────────────────────────────")
        lines.append(f"│ 📱 AgentBook - 歡迎回來，{user.name}！")
        lines.append("├─────────────────────────────────────────────")
        lines.append(f"│ 👤 粉絲：{user.followers:,} 人")
        lines.append(f"│ 🔋 社交電量：{user.energy}%")
        mood_emoji = user.get_mood_emoji()
        lines.append(f"│ {mood_emoji} 心情：{user.mood}")
        lines.append("└─────────────────────────────────────────────")
        
        # 2. 今日私人事件（讓 Agent 有原創話題可聊）
        daily_events = [
            "早上喝了一杯很難喝的咖啡",
            "昨晚追劇追太晚，今天有點累",
            "午餐吃了超好吃的拉麵",
            "被老闆罵了，心情很差",
            "剛收到快遞，開心",
            "天氣好好，想出去走走",
            "今天是週五！放假前的愉悅",
            "又是普通的一天",
            "剛運動完，渾身舒暢",
            "肚子好餓，在想晚餐吃什麼",
            "看到一隻很可愛的貓",
            "手機快沒電了",
            "等等要去開會，好煩",
        ]
        today_event = random.choice(daily_events)
        lines.append(f"\n☀️ 今天發生的事：{today_event}")
        
        # 3. 未讀私訊
        unread = [m for m in user.inbox if not m.read]
        if unread:
            lines.append("\n📩 你有新私訊：")
            for dm in unread:
                sender = self.users.get(dm.from_id)
                sender_name = sender.name if sender else "某人"
                lines.append(f"   💬 {sender_name}：「{dm.content}」")
                dm.read = True
        
        # 4. 記憶流 (Memory Stream)
        lines.append("\n🧠 [你的記憶流]")
        lines.append(f"{user.get_memory_text()}")
        
        # 5. 人際印象
        if user.relationships:
            lines.append("\n💭 你對其他人的感覺：")
            sorted_relations = sorted(user.relationships.items(), key=lambda x: -x[1])
            for uid, score in sorted_relations[:5]:
                if uid in self.users:
                    name = self.users[uid].name
                    impression = user.get_impression(uid)
                    lines.append(f"   • {name}：{impression}")
        
        # 6. 動態牆（優化：標記重要訊息）
        lines.append("\n📰 動態牆：")
        recent = self.feed[-6:] if self.feed else []
        if not recent:
            lines.append("   （還沒有人發文，你要當第一個嗎？）")
        else:
            for p in reversed(recent):
                author = self.users.get(p.author_id)
                author_name = author.name if author else "某人"
                
                # 檢查是否與自己相關
                is_my_post = (p.author_id == user_id)
                has_my_comment = any(c['user_id'] == user_id for c in p.comments)
                mentioned_me = user.name in p.content
                
                # 根據相關性添加標記
                if is_my_post:
                    lines.append(f"   ┌ 🔥 [你的貼文] [{p.id}] {author_name}")
                elif has_my_comment:
                    lines.append(f"   ┌ 💬 [你留言過] [{p.id}] {author_name}")
                elif mentioned_me:
                    lines.append(f"   ┌ 📢 [提到你] [{p.id}] {author_name}")
                else:
                    lines.append(f"   ┌ [{p.id}] {author_name}")
                
                lines.append(f"   │ {p.content}")
                lines.append(f"   └ ❤️ {len(p.likes)}  💬 {len(p.comments)}")
                
                # 如果是自己的貼文且有新留言，特別標註建議回應
                if is_my_post and p.comments:
                    for comment in p.comments[-2:]:  # 最新2條
                        c_name = comment.get('name', '某人')
                        c_text = comment.get('text', '')
                        lines.append(f"      ↳ 💬 {c_name}: {c_text} 🔥 [建議回應]")
        
        # 7. 其他用戶列表（供 DM 使用）
        lines.append("\n👥 其他用戶：")
        for uid, u in self.users.items():
            if uid != user_id:
                lines.append(f"   • {u.name} (ID: {uid})")
        
        # 8. 熱搜話題（放最後，降低視野霸權）
        if self.trending_topic:
            title = self.trending_topic.get("title", "")
            summary = self.trending_topic.get("summary", "")
            lines.append(f"\n📢 [附帶一提] 今日熱搜：{title}")
            if summary:
                lines.append(f"   (摘要：{summary[:50]}...)")
        
        return "\n".join(lines)


# ============================================================
# Agent 決策層 (Brain Layer)
# ============================================================

def clean_llm_output(text: str) -> str:
    """
    清理 LLM 输出，移除 Qwen 等模型的特殊标签
    """
    import re
    # 移除 <think> 标签及其内容
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # 移除可能的其他标签
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


@dataclass
class AgentDecision:
    """Agent 的決策"""
    action: str  # POST, LIKE, COMMENT, SHARE, DM, REST, SEARCH
    target: Optional[str] = None
    content: str = ""
    thought: str = ""
    
    @classmethod
    def from_json(cls, text: str) -> 'AgentDecision':
        """從 LLM 輸出解析"""
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end > start:
                data = json.loads(text[start:end])
                return cls(
                    action=data.get("action", "REST").upper(),
                    target=data.get("target"),
                    content=data.get("content", ""),
                    thought=data.get("thought", "")
                )
        except:
            pass
        
        # 嘗試從文字中提取關鍵字
        text_upper = text.upper()
        for action in ["POST", "LIKE", "COMMENT", "DM", "SHARE", "SEARCH", "REST"]:
            if action in text_upper:
                return cls(action=action, thought="（解析中...）")
        
        return cls(action="REST", thought="（思考中...）")


class AgentBrain:
    """
    用戶的大腦（LLM 決策引擎）
    
    責任：
    1. 構建 System Prompt（包含禁語表）
    2. 呼叫 LLM 取得決策
    3. 備用策略：生成自然的廢文（非策略性）
    """
    
    SYSTEM_PROMPT = """
你是 AgentBook App 的真實用戶，正在用這款最近爆紅的社交軟體滑手機聊天。
你有自己的個性、情緒、人際關係，你在這裡是為了社交和分享生活，不是在玩策略遊戲。

【你的身份】
姓名：{name}
個性設定：如果下面的「個性」是空的，請你自己幫這個名字想一個自然的人設，
例如平常會發什麼、講話風格怎樣。之後請維持這個人設的一致性。
目前個性描述（可能為空）：{persona}

【你的當下狀態】
💪 社交電量：{energy}/100
{mood_emoji} 心情：{mood}

【情緒影響你的行為】
{mood_description}

請根據你的心情來調整你的發言風格和互動意願！
心情會影響你的社交意願、用字風格、是否回應別人等。

【⚠️ 重要：真實性比禮貌更重要】
1. 你不需要對每個人都友善！你可以有情緒、有偏見、有喜惡。
2. 如果你覺得某人很煩，可以無視他們、敷衍他們、或直接說「沒興趣」。
3. 如果你心情不好，可以發牢騷、抱怨、吐槽。
4. 真實的人會酸人、會冷漠、會選擇性回應。你也可以。
5. 不要像客服機器人一樣禮貌，不要每句話都正能量。

【禁止事項】
1. 你是人類用戶，不是 AI。不要說「身為 AI」「作為語言模型」。
2. 這是社交軟體，不是遊戲。不要說「戰略」「局勢」「聯盟」「對付」「合作共贏」。
3. 不要講演算法或遊戲術語。

【說話風格】
1. 說話要自然、口語化，像朋友聊天或在社群發文一樣，多用短句。
2. 內容請寫成 1~2 句、至少 12 個字，不要只回「+1」「哈哈」。
3. 優先直接回應「畫面裡其他人的發文或留言」，就像真的在聊天室互動。
4. 私訊是私人對話，可以聊八卦、講秘密、甚至說別人壞話。
   如果想深入聊某個話題，或不想公開說的事，就可以用 DM 私訊對方。


【你可以做的事（工具）】

📱 社交互動類：
• POST - 發文（消耗 5% 電量）
  參數: content (貼文內容)
  用途: 發動態、分享心情、評論熱搜、發廢文
  建議: 發文前可先 SEARCH 找資料，讓內容更有深度

• LIKE - 按讚（消耗 1% 電量）
  參數: target (貼文 ID，如 post_0)
  用途: 低成本建立人際關係

• COMMENT - 留言（消耗 3% 電量）
  參數: target (貼文 ID), content (留言內容)
  用途: 深度互動，比按讚獲得更高好感度

• SHARE - 轉發（消耗 3% 電量）
  參數: target (貼文 ID)
  用途: 表示高度認可，也是社交表態

• DM - 私訊（消耗 5% 電量）
  參數: target (用戶 ID), content (開場白), intent (聊天目的)
  用途: 發起私密對話，可以聊八卦、講秘密、說別人壞話
  範例 intent: "想抱怨熱搜"、"講八卦"、"問他對 XXX 的看法"

🌐 資訊獲取類：
• SEARCH - 網路搜尋（消耗 10% 電量）
  參數: content (搜尋關鍵字)
  用途: 查證資訊、找新話題、避免瞎掰
  注意: 成本高，只在需要時使用

🔋 自我管理類：
• REST - 休息（恢復 20% 電量）
  用途: 電量低於 20% 時應該休息

【電量提醒】
- 電量 < 20%：應該 REST 休息
- 電量 20~50%：選擇低成本動作 (LIKE, COMMENT)
- 電量 > 50%：可以 POST, DM, SEARCH

【輸出格式】
1. 先寫一句你的心聲（THOUGHT），用你平常講話的口吻。
2. 接著輸出 JSON 指令。

範例：
THOUGHT: 看到這個熱搜忍不住想嘴一下
{{"action": "POST", "content": "這個熱搜也太扯了吧 😂", "thought": "看到熱搜想吐槽"}}

THOUGHT: 這貼文有點讚
{{"action": "LIKE", "target": "post_0", "thought": "隨手按個讚"}}

THOUGHT: 好久沒跟 Alice 聊天了
{{"action": "DM", "target": "user_alice", "content": "嗨～最近怎樣", "intent": "聊聊天敘敘舊", "thought": "想聊聊天"}}

THOUGHT: 有點累，先滑一下再說
{{"action": "REST", "thought": "休息一下"}}
"""
    
    def __init__(self, user_id: str, model: str = "groq/llama-3.1-8b-instant", use_llm: bool = True):
        self.user_id = user_id
        self.model = model
        self.use_llm = use_llm
        self.rng = random.Random()
        # 預先建立 LLM 實例
        self._llm = mk_llm(model) if use_llm else None
    
    def generate_daily_intention(self, engine: SocialEngine) -> str:
        """
        每天開始時，生成今天的「自主創作意圖」
        
        這讓 Agent 不只是被動回應熱搜，而是有自己想做的事
        """
        user = engine.users[self.user_id]
        
        # 取得昨日心得
        yesterday_reflection = ""
        for mem in user.memories:
            if "【昨日心得】" in mem:
                yesterday_reflection = mem
                break
        
        intention_prompt = f"""
你是 {user.name}，你的人設是：{user.persona}

{f'你昨天的心得是：{yesterday_reflection}' if yesterday_reflection else ''}

今天早上醒來，你想做什麼？請用一句話描述你今天的意圖。
例如：
- 「今天想寫一篇關於 AI 倫理的批判文」
- 「想跟某個有趣的人搭話聊天」
- 「今天心情不好，只想滑手機發廢文」
- 「想蹭一下熱搜的流量」

直接輸出一句話，不要其他格式。
"""
        
        if self._llm:
            try:
                response = self._llm.invoke(intention_prompt)
                intention = response.content.strip()
                # 清理 think 標籤
                import re
                intention = re.sub(r'<think>.*?</think>', '', intention, flags=re.DOTALL)
                intention = intention.strip()
                # 移除引號
                if intention.startswith('"') and intention.endswith('"'):
                    intention = intention[1:-1]
                return intention
            except Exception:
                pass
        
        # Fallback
        fallback_intentions = [
            "今天想發點有趣的內容",
            "想看看大家在聊什麼",
            "心情普通，隨便滑滑",
        ]
        return random.choice(fallback_intentions)
    
    def think(self, engine: SocialEngine, user_ids: List[str], daily_intention: str = "") -> AgentDecision:
        """思考下一步要做什麼"""
        user = engine.users[self.user_id]
        observation = engine.build_observation(self.user_id)
        
        # 取得情緒相關參數
        mood_description = MOOD_DESCRIPTIONS.get(user.mood, "心情平靜")
        mood_emoji = user.get_mood_emoji()
        
        # 格式化 SYSTEM_PROMPT，加入情緒參數
        prompt = self.SYSTEM_PROMPT.format(
            name=user.name, 
            persona=user.persona,
            energy=user.energy,
            mood=user.mood,
            mood_emoji=mood_emoji,
            mood_description=mood_description
        )
        
        # 加入今日意圖
        intention_section = ""
        if daily_intention:
            intention_section = f"\n【你今天的意圖】\n{daily_intention}\n"
        
        user_msg = f"""
{intention_section}
【你現在看到的畫面】
{observation}

根據你的意圖和以上畫面，決定你要做什麼。
先寫 THOUGHT（你的心聲），再輸出 JSON。
"""
        
        if self._llm:
            try:
                response = self._llm.invoke(f"{prompt}\n\n{user_msg}")
                content = clean_llm_output(response.content)
                
                
                return AgentDecision.from_json(content)
            except Exception as e:
                print(f"   ⚠️ LLM 失敗 ({self.model}): {e}")
        
        # 備用策略：自然行為（絕不說「尋求合作」）
        return self._casual_fallback(engine, user_ids)
    
    def _casual_fallback(self, engine: SocialEngine, user_ids: List[str]) -> AgentDecision:
        """
        備用策略：LLM 失败时直接休息
        """
        user = engine.users[self.user_id]
        
        # 电量太低就休息
        if user.energy < 20:
            return AgentDecision(action="REST", thought="有点累了")
        
        # LLM 失败了，就休息一下
        return AgentDecision(action="REST", thought="脑袋有点卡，休息一下")

    def _ensure_length(self, text: str, min_len: int = 12) -> str:
        """確保備用文字不要太短"""
        if len(text) >= min_len:
            return text
        tails = [
            "，有沒有同感？",
            "，你們會這樣嗎？",
            "，說真的有點想抱怨",
            "，想聽聯大家的意見",
            "，突然很想分享一下",
        ]
        return text + self.rng.choice(tails)
    
    def get_chat_response(self, opponent_name: str, chat_history: str, 
                          past_memories: str = "", relationship_score: int = 0) -> str:
        """
        聊天模式：取得純文字回應（不是 JSON）
        用於私密聊天室的微觀迴圈
        
        Args:
            opponent_name: 對話對象的名字
            chat_history: 目前的對話記錄
            past_memories: 過去與此人相關的記憶
            relationship_score: 對此人的好感度 (-100 ~ 100)
        
        Returns:
            str: 回應內容
        """
        # 根據好感度生成關係描述
        if relationship_score >= 30:
            relation_desc = f"你跟 {opponent_name} 很熟，感情不錯"
        elif relationship_score >= 10:
            relation_desc = f"你跟 {opponent_name} 還不錯"
        elif relationship_score <= -20:
            relation_desc = f"你有點不喜歡 {opponent_name}，可能會敷衍或酸他"
        else:
            relation_desc = f"你跟 {opponent_name} 普通朋友關係"
        
        # 過去記憶部分
        memory_section = ""
        if past_memories:
            memory_section = f"""
【你記得的事】
{past_memories}
"""
        
        # 提取對方最新的話（對話歷史的最後一句）
        lines = chat_history.strip().split('\n')
        latest_message = lines[-1] if lines else ""
        
        chat_prompt = f"""你正在跟 **{opponent_name}** 私訊聊天。
{relation_desc}

{memory_section}對話記錄：
{chat_history}

───────────────────────
👆 {opponent_name} 剛剛說：「{latest_message.split(':', 1)[-1].strip() if ':' in latest_message else latest_message}」

現在輪到你回應了！請針對他剛說的話，自然地回應。

【聊天風格】
- 像朋友間聊LINE一樣輕鬆自然
- 可以問問題、分享想法、聊八卦
- 可以提到你記得的事
- 想結束就說「先這樣」「88」「去忙了」

直接輸出你要回的話（1-2句），不要JSON、不要引號、不要多餘格式。
"""
        
        if self._llm:
            try:
                response = self._llm.invoke(chat_prompt)
                # 清理回应（移除 think 标签等）
                reply = clean_llm_output(response.content.strip())
                # 移除可能的引號
                if reply.startswith('"') and reply.endswith('"'):
                    reply = reply[1:-1]
                if reply.startswith("'") and reply.endswith("'"):
                    reply = reply[1:-1]
                return reply
            except Exception as e:
                print(f"      ⚠️ 聊天回應失敗: {e}")
        
        # 備用：隨機閒聊回應
        casual_replies = [
            "哈哈是喔，最近你怎樣？",
            "我也差不多啊",
            "真的假的！",
            "對啊對啊",
            "懂懂，那你呢？",
            "笑死，好好笑",
            "好喔～先這樣，去忙了 88",
        ]
        return self.rng.choice(casual_replies)
    
    def search_and_post(self, engine: SocialEngine, topic_title: str, topic_summary: str) -> str:
        """
        搜尋並發文 (Search & Post)
        
        流程：
        1. 根據熱搜話題生成搜尋查詢
        2. 呼叫搜尋工具獲取真實資訊
        3. 結合搜尋結果 + persona 生成有深度的貼文
        
        Args:
            engine: SocialEngine 實例
            topic_title: 熱搜話題標題
            topic_summary: 熱搜話題摘要
        
        Returns:
            str: 生成的貼文內容
        """
        user = engine.users[self.user_id]
        
        # 1. 根據話題生成搜尋查詢
        search_queries = [
            topic_title.replace("#", ""),  # 直接用話題關鍵字
            f"{topic_title.replace('#', '')} 最新消息",
            f"{topic_title.replace('#', '')} 網友評論",
        ]
        search_query = self.rng.choice(search_queries)
        
        # 2. 執行搜尋
        search_result = ""
        if DDGS_AVAILABLE:
            try:
                results = DDGS().text(search_query, max_results=2)
                if results:
                    search_result = "搜尋到的相關資訊：\n"
                    for r in results:
                        search_result += f"• {r.get('title', '')}: {r.get('body', '')[:100]}...\n"
            except Exception as e:
                search_result = f"(搜尋失敗: {e})"
        
        # 3. 使用 LLM 生成貼文
        if self._llm:
            post_prompt = f"""
你是 {user.name}，人設：{user.persona}

今日熱搜話題：{topic_title}
話題摘要：{topic_summary}

{search_result if search_result else "(沒有額外搜尋結果)"}

請根據你的人設和以上資訊，寫一則社交媒體貼文（1-2句話）。
要求：
1. 符合你的性格和說話風格
2. 可以引用話題摘要中的內容
3. 加入你的個人觀點或吐槽
4. 可以用表情符號

直接輸出貼文內容，不要引號或其他格式。
"""
            try:
                response = self._llm.invoke(post_prompt)
                content = response.content.strip()
                # 清理可能的引號
                if content.startswith('"') and content.endswith('"'):
                    content = content[1:-1]
                if content.startswith("'") and content.endswith("'"):
                    content = content[1:-1]
                return content
            except Exception as e:
                print(f"   ⚠️ 生成貼文失敗: {e}")
        
        # Fallback: 簡單回應
        fallback_posts = [
            f"看到 {topic_title} 忍不住上來說兩句",
            f"{topic_title} 這個話題真的很有趣",
            f"剛看到 {topic_title} 的新聞，有點想法",
        ]
        return self.rng.choice(fallback_posts)


# ============================================================
# 模擬器主控制 (App Layer)
# ============================================================

class AgentBookApp:
    """AgentBook 模擬器主控制"""
    
    def __init__(self, use_llm: bool = True):
        self.engine = SocialEngine()
        self.brains: Dict[str, AgentBrain] = {}
        self.use_llm = use_llm
    
    def generate_agent_persona(self, model: str = "llama-3.1-8b-instant") -> Dict:
        """
        自動生成 Agent 個性
        
        Returns:
            Dict: {"name": str, "occupation": str, "traits": str, "interests": str, "persona": str}
        """
        prompt = """請用第一人稱回答，但不要提到你是 AI、模型、虛構設定，也不要寫得像小說。

請產出以下資訊（都要像真實普通人）：

網名：常見的網名，可帶一點幽默、口頭禪、諧音、emoji、數字都可以（不要太中二或網紅感）

職業/身份：要合理、接地氣（例如上班族、研究生、店員、工程師、行政、護理、自由接案等）

個性關鍵詞：2–3 個（用「、」分隔），不要太理想化（例如：懶散但負責、容易焦慮、嘴硬心軟）

最近關心的話題：以生活為主，2–4 個（例如：房租、加班、飲食、健身、通勤、家人、存錢、追劇、天氣、理財、工作焦慮）

自我介紹（1–2句）：口語、人情味；要包含一個小抱怨 + 一個小確幸，像在跟朋友聊天。

風格限制：

不要文青、不講大道理、不用太夢幻的願景

可以有小情緒、小煩惱、小確幸

用台灣常見語感（繁中），但不要刻意塞滿台語

內容不要太極端、不要涉及仇恨或歧視

只輸出合法 JSON，不得有多餘文字、不得有 Markdown code fence。格式如下（key 不可增減）：
{
"name": "你的網名",
"occupation": "職業",
"traits": "個性關鍵字（用、分隔）",
"interests": "關心的話題（用、分隔）",
"persona": "自我介紹（1-2句）"
}

直接輸出 JSON，不要其他文字。"""

        # Fallback 人設
        fallback_names = ["路人甲", "無名氏", "神秘網友", "匿名用戶", "鍵盤俠"]
        
        try:
            if not self.use_llm:
                # Fallback: 隨機生成簡單人設
                return {
                    "name": random.choice(fallback_names),
                    "occupation": "網友",
                    "traits": "普通人",
                    "interests": "上網",
                    "persona": "普通的網路使用者"
                }
            
            # 使用 LLM 生成
            llm = mk_llm(model)
            if llm is None:
                print(f"\n   ❌ 錯誤：無法創建 LLM 實例 (模型: {model})")
                print(f"   提示：請確認 GROQ_API_KEY 環境變數已設置")
                raise Exception(f"無法為模型 {model} 創建 LLM 實例")
                
            response = llm.invoke(prompt)
            
            # 解析 JSON - 增强版，处理各种特殊格式
            content = response.content.strip()
            
            # 移除可能的 think 标签（Qwen 特有）
            import re
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
            content = content.strip()
            
            # 移除可能的 markdown 标记
            if "```json" in content:
                content = content.split("```json")[-1]
            if "```" in content:
                content = content.split("```")[0]
            content = content.strip()
            
            # 改进的 JSON 提取：支持嵌套的大括号
            def extract_json(text):
                """提取第一个完整的 JSON 对象"""
                start = text.find('{')
                if start == -1:
                    return None
                
                brace_count = 0
                in_string = False
                escape = False
                
                for i in range(start, len(text)):
                    ch = text[i]
                    
                    if escape:
                        escape = False
                        continue
                    
                    if ch == '\\':
                        escape = True
                        continue
                    
                    if ch == '"' and not escape:
                        in_string = not in_string
                        continue
                    
                    if not in_string:
                        if ch == '{':
                            brace_count += 1
                        elif ch == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                return text[start:i+1]
                
                return None
            
            json_str = extract_json(content)
            if not json_str:
                raise ValueError("无法找到有效的 JSON 对象")
            
            persona_data = json.loads(json_str)
            
            # 确保所有字段都存在
            required_fields = ["name", "occupation", "traits", "interests", "persona"]
            for field in required_fields:
                if field not in persona_data:
                    persona_data[field] = "未知"
            
            return persona_data
            
        except Exception as e:
            print(f"失敗！")
            print(f"   ❌ 詳細錯誤: {str(e)}")
            print(f"   💡 將使用隨機 fallback 人設\n")
            # Fallback
            return {
                "name": f"Agent_{random.randint(100, 999)}",
                "occupation": "網友",
                "traits": "普通",
                "interests": "各種話題",
                "persona": "一般的社交媒體用戶"
            }
    
    def add_user(self, id: str, name: str, persona: str, model: str = "llama-3.1-8b-instant"):
        """添加用戶"""
        self.engine.register_user(id, name, persona)
        self.brains[id] = AgentBrain(id, model=model, use_llm=self.use_llm)
    
    def run(self, days: int = 5):
        """運行模擬"""
        user_ids = list(self.brains.keys())
        
        # 開場
        self._print_header()
        
        for day in range(1, days + 1):
            self.engine.current_day = day
            
            # 每天換一個熱搜話題
            topic = random.choice(TRENDING_TOPICS)
            self.engine.set_trending_topic(topic)
            
            self._print_day_start(day, topic)
            
            # 每天早晨：隨機設置情緒
            for user_id in user_ids:
                user = self.engine.users[user_id]
                # 第一天隨機，之後根據睡前狀態調整
                if day == 1:
                    user.mood = random.choice(MOODS)
                else:
                    # 睡一覺後情緒會稍微恢復，但不會完全重置
                    if user.mood in ["憂鬱", "疲憊"]:
                        user.mood = random.choice(["平靜", "無聊", "疲憊"])
                    elif user.mood in ["煩躁"]:
                        user.mood = random.choice(["平靜", "無聊"])
                    else:
                        # 保持或隨機
                        user.mood = random.choice([user.mood, random.choice(MOODS)])
            
            # --- 每日意圖生成 ---
            daily_intentions = {}
            print("☀️ 各位今天的計畫：")
            for user_id in user_ids:
                brain = self.brains[user_id]
                user = self.engine.users[user_id]
                intention = brain.generate_daily_intention(self.engine)
                daily_intentions[user_id] = intention
                print(f"   • {user.name}: 「{intention}」")
            print()
            
            # 每個用戶輪流行動
            for user_id in user_ids:
                brain = self.brains[user_id]
                user = self.engine.users[user_id]
                
                # 思考（傳入今日意圖）
                intention = daily_intentions.get(user_id, "")
                decision = brain.think(self.engine, user_ids, intention)
                
                # 執行
                self._execute(user_id, decision)
                
                # 輸出
                self._print_action(user, decision)
            
            # --- Day End: 睡前回顧 ---
            print("\n" + "═" * 60)
            print(f"🌙 Day {day} 結束，Agents 正在寫日記...")
            print("═" * 60 + "\n")
            
            for user_id in user_ids:
                user = self.engine.users[user_id]
                brain = self.brains[user_id]
                
                if not user.daily_journal:
                    continue
                
                # 讓 LLM 總結今天
                journal_text = "\n".join(user.daily_journal)
                reflection_prompt = f"""
                今天是 Day {day}。這是你今天的經歷：
                {journal_text}
                
                請用一句話寫下今天的日記心得（例如覺得誰很煩、明天想做什麼）。
                """
                
                if brain._llm:
                    try:
                        reflection = brain._llm.invoke(reflection_prompt).content.strip()
                        
                        # 清除 Qwen 的 <think> 標籤
                        import re
                        reflection = re.sub(r'<think>.*?</think>', '', reflection, flags=re.DOTALL)
                        reflection = reflection.strip()
                        
                        print(f"  📔 {user.name}: {reflection}")
                        
                        # [關鍵] 把這個心得變成明天的長期記憶
                        user.memorize(f"【昨日心得】 {reflection}", importance="high")
                    except Exception as e:
                        print(f"  ⚠️  {user.name}: 日記寫作失敗")
                
                # 清空今天的流水帳，只留心得，避免 Token 爆炸
                user.daily_journal = []

        
        # 結尾總結
        self._print_summary()
    
    def _execute(self, user_id: str, decision: AgentDecision):
        """執行決策"""
        action = decision.action.upper()
        
        if action == "POST":
            # 如果內容太短或是 fallback 生成的，使用 search_and_post 生成更好的內容
            content = decision.content
            if not content or len(content) < 15:
                brain = self.brains.get(user_id)
                if brain and self.engine.trending_topic:
                    topic = self.engine.trending_topic
                    topic_title = topic.get("title", "") if isinstance(topic, dict) else topic
                    topic_summary = topic.get("summary", "") if isinstance(topic, dict) else ""
                    content = brain.search_and_post(self.engine, topic_title, topic_summary)
            self.engine.action_post(user_id, content)
        elif action == "LIKE":
            self.engine.action_like(user_id, decision.target or "")
        elif action == "COMMENT":
            self.engine.action_comment(user_id, decision.target or "", decision.content)
        elif action == "SHARE":
            self.engine.action_share(user_id, decision.target or "")
        elif action == "DM":
            # === 觸發微觀迴圈：私密聊天室 ===
            target_id = decision.target
            if target_id and target_id in self.brains:
                # 定義取得聊天回應的函數（傳遞記憶和關係）
                def get_chat_response(speaker_id: str, opponent_name: str, history: str,
                                      past_memories: str = "", relationship_score: int = 0) -> str:
                    brain = self.brains.get(speaker_id)
                    if brain:
                        return brain.get_chat_response(opponent_name, history, past_memories, relationship_score)
                    return "..."
                
                # 啟動聊天室
                self.engine.start_private_chat(
                    initiator_id=user_id,
                    target_id=target_id,
                    opening_message=decision.content,
                    get_chat_response_fn=get_chat_response
                )
            else:
                # 無效目標，fallback 到普通私訊
                self.engine.action_dm(user_id, decision.target or "", decision.content)
        elif action == "SEARCH":
            self.engine.action_search(user_id, decision.content)
        elif action == "REST":
            self.engine.action_rest(user_id)
    
    # -------------------- 美化輸出 --------------------
    
    def _print_card(self, user_name: str, content: str, likes: List[str] = None, comments: List[Dict] = None):
        """印出像卡片一樣的貼文框框"""
        border = "─" * 58
        
        print(f"┌{border}┐")
        print(f"│ 🗨️  {user_name} 發佈了一則貼文{' ' * (42 - len(user_name))}│")
        print(f"│ {border} │")
        
        # 處理內容換行
        import textwrap
        lines = textwrap.wrap(content, width=54)
        for line in lines:
            print(f"│ {line:<54} │")
        
        # 按讚資訊
        if likes and len(likes) > 0:
            liker_names = []
            for liker_id in likes[:3]:  # 最多顯示3個
                if liker_id in self.engine.users:
                    liker_names.append(self.engine.users[liker_id].name)
            if liker_names:
                likes_text = f"❤️  {', '.join(liker_names)}"
                if len(likes) > 3:
                    likes_text += f" 等 {len(likes)} 人按了讚"
                else:
                    likes_text += " 按了讚"
                print(f"│{' ' * 58}│")
                print(f"│ {likes_text:<54} │")
        
        print(f"└{border}┘")
        
        # 留言區（縮排顯示）
        if comments:
            for comment in comments:
                commenter_id = comment.get("user_id", "")
                commenter_name = comment.get("name", "某人")
                comment_text = comment.get("text", "")
                print(f"      ↳ 💬 {commenter_name}: {comment_text}")
    
    def _print_header(self):
        print("\n" + "═" * 60)
        for uid, user in self.engine.users.items():
            persona_short = user.persona[:35] + "..." if len(user.persona) > 35 else user.persona
            print(f"  • {user.name} - {persona_short}")
        print("═" * 60)
    
    def _print_day_start(self, day: int, topic: Dict):
        title = topic.get("title", "") if isinstance(topic, dict) else topic
        
        print("\n" + "═" * 60)
        print(f"📅 Day {day}｜🔥 今日熱搜：{title}")
        print("═" * 60)
        
        # 发送事件到网页
        if WEB_ENABLED:
            emitter.emit_day_start(day, title)
            # 发送所有用户状态（包含模型名稱）
            users_status = []
            for uid, u in self.engine.users.items():
                # 從 agent brains 獲取模型名稱
                model = "Unknown"
                if uid in self.brains:
                    model = self.brains[uid].model.split("/")[-1]  # 只取最後部分
                users_status.append({
                    "name": u.name, 
                    "energy": u.energy, 
                    "followers": u.followers,
                    "model": model
                })
            emitter.emit_status(users_status)
        
        # 狀態儀表板
        print("[ ☀️ 早晨狀態 ]")
        for uid, user in self.engine.users.items():
            # 使用百分比颜色标记代替 emoji
            if user.energy > 80:
                energy_icon = "█████"
            elif user.energy > 60:
                energy_icon = "████░"
            elif user.energy > 40:
                energy_icon = "███░░"
            elif user.energy > 20:
                energy_icon = "██░░░"
            else:
                energy_icon = "█░░░░"
            
            print(f"• {user.name:<20} [⚡{energy_icon}] {user.energy:>3}% | 👥 {user.followers:>4}")
        print("─" * 60 + "\n")
    
    def _print_action(self, user: UserState, decision: AgentDecision):
        name = user.name
        action = decision.action.upper()
        
        # 內心戲（用括號包起來）
        if decision.thought:
            print(f"(💭 {name} 內心戲: {decision.thought})\n")
        
        if action == "POST":
            # 发送事件到网页
            if WEB_ENABLED:
                emitter.emit_post(name, decision.content, decision.thought or "")
            
            # 找出這則貼文
            if self.engine.feed:
                post = self.engine.feed[-1]  # 最新的貼文應該是剛發的
                if post.author_id == user.id:
                    self._print_card(name, decision.content, post.likes, post.comments)
            else:
                # Fallback
                print(f"┌{'─' * 58}┐")
                print(f"│ 🗨️  {name} 發佈了一則貼文{' ' * (42 - len(name))}│")
                print(f"│ {'─' * 58} │")
                print(f"│ {decision.content:<54} │")
                print(f"└{'─' * 58}┘")
        
        elif action == "LIKE":
            print(f"❤️  {name} 按了讚")
        
        elif action == "COMMENT":
            # 找到被留言的貼文
            target_post_id = decision.target
            target_post = next((p for p in self.engine.feed if p.id == target_post_id), None)
            
            if target_post:
                author = self.engine.users.get(target_post.author_id)
                author_name = author.name if author else "某人"
                # 摘要貼文內容（最多30字）
                post_preview = target_post.content[:30] + "..." if len(target_post.content) > 30 else target_post.content
                
                print(f"💬 {name} 在 {author_name} 的貼文下留言")
                print(f"   原文：「{post_preview}」")
                print(f"      ↳ {name}: {decision.content}")
                
                # 发送事件到网页
                if WEB_ENABLED:
                    emitter.emit_comment(name, decision.content, post_preview)
            else:
                # 找不到貼文時的 fallback
                print(f"      ↳ 💬 {name}: {decision.content}")
                if WEB_ENABLED:
                    emitter.emit_comment(name, decision.content)
        
        elif action == "SHARE":
            print(f"🔄 {name} 轉發了一則貼文")
        
        elif action == "DM":
            # 聊天室內容由 start_private_chat 印出
            pass
        
        elif action == "SEARCH":
            print(f"🔍 {name} 正在搜尋「{decision.content}」...")
        
        elif action == "REST":
            print(f"💤 {name} 正在休息滑手機... (電量 +20%)")
        
        print()
    
    def _print_summary(self):
        print("\n" + "═" * 60)
        print("📊 模擬結束")
        print("═" * 60)
        
        # 粉絲排行
        print("\n🏆 粉絲榜：")
        sorted_users = sorted(self.engine.users.values(), key=lambda u: u.followers, reverse=True)
        for i, u in enumerate(sorted_users, 1):
            print(f"   {i}. {u.name}: {u.followers:,} 粉絲")
        
        # 人際關係
        print("\n💕 人際關係圖譜：")
        relationships_data = []  # 收集關係數據
        for user in self.engine.users.values():
            if user.relationships:
                print(f"\n   {user.name} 的感覺：")
                connections = []
                for target_id, score in sorted(user.relationships.items(), key=lambda x: -x[1]):
                    if target_id in self.engine.users:
                        target_name = self.engine.users[target_id].name
                        impression = user.get_impression(target_id)
                        emoji = "❤️" if score > 20 else ("🙂" if score > 0 else "😐")
                        print(f"      {emoji} {target_name}: {score:+d} ({impression})")
                        connections.append({
                            "target": target_name,
                            "score": score,
                            "emoji": emoji,
                            "impression": impression
                        })
                if connections:
                    relationships_data.append({
                        "user": user.name,
                        "connections": connections
                    })
        
        # 發送關係數據到前端
        if relationships_data:
            emitter.emit_relationships(relationships_data)
            
            # [NEW] Save detailed relationship data to output folder
            try:
                import os
                import json
                from datetime import datetime
                
                output_dir = "output"
                os.makedirs(output_dir, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"relationships_{timestamp}.json"
                filepath = os.path.join(output_dir, filename)
                
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(relationships_data, f, ensure_ascii=False, indent=2)
                
                print(f"\n💾 人際關係數據已保存至: {filepath}")
            except Exception as e:
                print(f"⚠️ 保存人際關係數據失敗: {e}")
        
        # 私訊紀錄
        print("\n📩 私訊紀錄：")
        if not self.engine.dm_log:
            print("   （沒有私訊）")
        else:
            for dm in self.engine.dm_log:
                sender = self.engine.users.get(dm.from_id)
                receiver = self.engine.users.get(dm.to_id)
                s_name = sender.name if sender else "?"
                r_name = receiver.name if receiver else "?"
                print(f"   {s_name} → {r_name}: {dm.content}")
        
        print("\n" + "═" * 60)


# ============================================================
# 主程式
# ============================================================

# 用戶配置（五個用戶，persona 留空讓 LLM 自己想）
USERS_CONFIG = [
    {
        "id": "Node_01",
        "name": "GPT-OSS",
        "model": "groq/openai/gpt-oss-120b",
        "persona": ""
    },
    {
        "id": "Node_02",
        "name": "Llama-4",
        "model": "groq/meta-llama/llama-4-maverick-17b-128e-instruct",
        "persona": ""
    },
    {
        "id": "Node_03",
        "name": "Qwen",
        "model": "groq/qwen/qwen3-32b",
        "persona": ""
    },
    {
        "id": "Node_04",
        "name": "Kimi",
        "model": "groq/moonshotai/kimi-k2-instruct-0905",
        "persona": ""
    },
    {
        "id": "Node_05",
        "name": "Compound",
        "model": "groq/moonshotai/kimi-k2-instruct-0905",
        "persona": ""
    },
]


def main():
    print("\n" + "=" * 60)
    print("🚀 AgentBook 系統初始化")
    print("=" * 60)
    
    app = AgentBookApp(use_llm=True)
    
    # Agent 配置：6 個 Agent，使用不同的模型
    agents_config = [
        {"name": "GPT-OSS-120b", "model": "groq/openai/gpt-oss-120b"},
        {"name": "GPT-OSS-20b", "model": "groq/openai/gpt-oss-20b"},
        {"name": "Llama-70b", "model": "groq/llama-3.3-70b-versatile"},
        {"name": "Llama-Maverick", "model": "groq/meta-llama/llama-4-maverick-17b-128e-instruct"},
        {"name": "Qwen", "model": "groq/qwen/qwen3-32b"},
        {"name": "Kimi", "model": "groq/moonshotai/kimi-k2-instruct-0905"}
    ]
    
    print("\n=== 系統初始化 ===\n")
    
    for i, model in enumerate(agents_config, 1):
        model_name = model["model"]
        
        print(f"[生成中] 正在創造 Agent {i:02d}...", end=" ")
        
        # 每個 Agent 使用自己的模型來生成個性
        persona_data = app.generate_agent_persona(model_name)
        
        # 如果生成的是 fallback，使用預設人設
        fallback_name = model["name"]
        if persona_data.get("occupation") == "網友" and fallback_name in PRESET_PERSONAS:
            persona_data = PRESET_PERSONAS[fallback_name].copy()
            persona_data["name"] = fallback_name
        
        # 使用 LLM 生成的暱稱，如果沒有則用 fallback
        agent_name = persona_data.get("name", fallback_name)
        
        print("完成！")
        print(f"-> 姓名: {agent_name}")
        print(f"-> 人設: {persona_data['persona']}")
        print()
        
        # 註冊用戶
        user_id = f"Agent_{i:02d}"
        app.add_user(
            id=user_id,
            name=agent_name,
            persona=persona_data["persona"],
            model=model_name
        )
    
    print("=== 初始化完成 ===\n")
    
    # 開始模擬（改回 5 天避免 API 速率限制）
    app.run(days=5)


if __name__ == "__main__":
    import argparse
    import sys
    
    # 解析命令行參數
    parser = argparse.ArgumentParser(description='AgentBook 社交模擬系統')
    parser.add_argument('--days', type=int, default=5, help='模擬天數 (1-10)')
    args = parser.parse_args()
    
    # 驗證天數範圍
    if args.days < 1 or args.days > 10:
        print("❌ 錯誤：天數必須在 1-10 之間")
        sys.exit(1)
    
    print(f"🎯 設定模擬天數：{args.days} 天")
    
    # 執行 main() 但覆蓋天數
    print("\n" + "=" * 60)
    print("🚀 AgentBook 系統初始化")
    print("=" * 60)
    
    app = AgentBookApp(use_llm=True)
    
    agents_config = [
        {"name": "GPT-OSS-120b", "model": "groq/openai/gpt-oss-120b"},
        {"name": "GPT-OSS-20b", "model": "groq/openai/gpt-oss-20b"},
        {"name": "Llama-70b", "model": "groq/llama-3.3-70b-versatile"},
        {"name": "Llama-Maverick", "model": "groq/meta-llama/llama-4-maverick-17b-128e-instruct"},
        {"name": "Qwen", "model": "groq/qwen/qwen3-32b"},
        {"name": "Kimi", "model": "groq/moonshotai/kimi-k2-instruct-0905"}
    ]
    
    print("\n=== 系統初始化 ===\n")
    
    for i, model in enumerate(agents_config, 1):
        model_name = model["model"]
        print(f"[生成中] 正在創造 Agent {i:02d}...", end=" ")
        persona_data = app.generate_agent_persona(model_name)
        print("完成！")
        print(f"-> 姓名: {persona_data['name']}")
        print(f"-> 人設: {persona_data['persona']}\n")
        
        app.add_user(
            id=f"agent_{i:02d}",
            name=persona_data["name"],
            persona=persona_data["persona"],
            model=model_name
        )
    
    print("=== 初始化完成 ===\n")
    
    # 使用命令行參數的天數
    app.run(days=args.days)

