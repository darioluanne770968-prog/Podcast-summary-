"""
内容 DNA 分析模块

提取播客的独特风格特征
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import json
import numpy as np

from ..utils import get_logger

logger = get_logger(__name__)


@dataclass
class PodcastFingerprint:
    """播客指纹"""
    podcast_id: str
    podcast_name: str

    # 语言特征
    vocabulary_richness: float = 0.0  # 词汇丰富度
    avg_sentence_length: float = 0.0  # 平均句长
    formality_score: float = 0.0  # 正式度
    humor_index: float = 0.0  # 幽默指数

    # 声音特征
    speaking_rate: float = 0.0  # 语速 (词/分钟)
    pause_frequency: float = 0.0  # 停顿频率
    pitch_variation: float = 0.0  # 音调变化
    energy_level: float = 0.0  # 能量水平

    # 内容特征
    topic_diversity: float = 0.0  # 话题多样性
    depth_score: float = 0.0  # 深度分数
    guest_frequency: float = 0.0  # 嘉宾频率
    storytelling_index: float = 0.0  # 叙事指数

    # 互动特征
    question_frequency: float = 0.0  # 提问频率
    audience_engagement: float = 0.0  # 听众参与度
    call_to_action_rate: float = 0.0  # 行动号召率

    # 成功因素
    success_factors: List[str] = field(default_factory=list)
    unique_elements: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "podcast_id": self.podcast_id,
            "podcast_name": self.podcast_name,
            "language_features": {
                "vocabulary_richness": self.vocabulary_richness,
                "avg_sentence_length": self.avg_sentence_length,
                "formality_score": self.formality_score,
                "humor_index": self.humor_index,
            },
            "audio_features": {
                "speaking_rate": self.speaking_rate,
                "pause_frequency": self.pause_frequency,
                "pitch_variation": self.pitch_variation,
                "energy_level": self.energy_level,
            },
            "content_features": {
                "topic_diversity": self.topic_diversity,
                "depth_score": self.depth_score,
                "guest_frequency": self.guest_frequency,
                "storytelling_index": self.storytelling_index,
            },
            "interaction_features": {
                "question_frequency": self.question_frequency,
                "audience_engagement": self.audience_engagement,
                "call_to_action_rate": self.call_to_action_rate,
            },
            "success_factors": self.success_factors,
            "unique_elements": self.unique_elements,
        }

    def to_vector(self) -> List[float]:
        """转换为特征向量"""
        return [
            self.vocabulary_richness,
            self.avg_sentence_length / 50,  # 归一化
            self.formality_score,
            self.humor_index,
            self.speaking_rate / 200,
            self.pause_frequency,
            self.pitch_variation,
            self.energy_level,
            self.topic_diversity,
            self.depth_score,
            self.guest_frequency,
            self.storytelling_index,
            self.question_frequency,
            self.audience_engagement,
            self.call_to_action_rate,
        ]


class ContentDNA:
    """
    内容 DNA 分析器

    功能：
    - 提取播客风格指纹
    - 分析节奏和结构
    - 识别成功因素
    - 比较播客相似度
    """

    def __init__(self, llm_provider: str = "openai"):
        self.llm_provider = llm_provider
        self._fingerprints: Dict[str, PodcastFingerprint] = {}

    async def analyze_podcast(
        self,
        podcast_id: str,
        podcast_name: str,
        episodes: List[Dict],
    ) -> PodcastFingerprint:
        """
        分析播客 DNA

        Args:
            podcast_id: 播客 ID
            podcast_name: 播客名称
            episodes: 节目列表

        Returns:
            播客指纹
        """
        fingerprint = PodcastFingerprint(
            podcast_id=podcast_id,
            podcast_name=podcast_name,
        )

        # 聚合分析数据
        all_transcripts = []
        all_keywords = []
        all_durations = []
        guest_count = 0

        for ep in episodes:
            if ep.get("transcript"):
                all_transcripts.append(ep["transcript"][:2000])
            all_keywords.extend(ep.get("keywords", []))
            if ep.get("duration"):
                all_durations.append(ep["duration"])
            if ep.get("guests"):
                guest_count += 1

        # 计算语言特征
        if all_transcripts:
            fingerprint = await self._analyze_language_features(
                fingerprint, all_transcripts
            )

        # 计算内容特征
        fingerprint.topic_diversity = self._calculate_diversity(all_keywords)
        fingerprint.guest_frequency = guest_count / len(episodes) if episodes else 0

        # 使用 LLM 分析成功因素
        fingerprint = await self._analyze_success_factors(
            fingerprint, episodes
        )

        self._fingerprints[podcast_id] = fingerprint
        logger.info(f"完成播客 DNA 分析: {podcast_name}")

        return fingerprint

    async def _analyze_language_features(
        self,
        fingerprint: PodcastFingerprint,
        transcripts: List[str],
    ) -> PodcastFingerprint:
        """分析语言特征"""
        combined_text = " ".join(transcripts)

        # 基本统计
        words = combined_text.split()
        sentences = combined_text.replace("。", ".").replace("！", "!").replace("？", "?").split(".")

        # 词汇丰富度
        unique_words = set(words)
        fingerprint.vocabulary_richness = len(unique_words) / len(words) if words else 0

        # 平均句长
        sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
        fingerprint.avg_sentence_length = np.mean(sentence_lengths) if sentence_lengths else 0

        # 使用 LLM 分析更复杂的特征
        prompt = f"""分析以下播客文本的风格特征：

文本片段：
{combined_text[:3000]}

请评估（0-1分）：
1. 正式度 (formality)
2. 幽默指数 (humor)
3. 深度分数 (depth)
4. 叙事指数 (storytelling)
5. 提问频率 (questions)

返回 JSON 格式：
{{"formality": 0.7, "humor": 0.3, "depth": 0.8, "storytelling": 0.6, "questions": 0.4}}"""

        try:
            response = await self._call_llm(prompt)
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                fingerprint.formality_score = data.get("formality", 0.5)
                fingerprint.humor_index = data.get("humor", 0.3)
                fingerprint.depth_score = data.get("depth", 0.5)
                fingerprint.storytelling_index = data.get("storytelling", 0.5)
                fingerprint.question_frequency = data.get("questions", 0.3)
        except Exception as e:
            logger.error(f"语言特征分析失败: {e}")

        return fingerprint

    async def _analyze_success_factors(
        self,
        fingerprint: PodcastFingerprint,
        episodes: List[Dict],
    ) -> PodcastFingerprint:
        """分析成功因素"""
        # 提取样本内容
        sample_content = []
        for ep in episodes[:5]:
            sample_content.append({
                "title": ep.get("title", ""),
                "summary": ep.get("summary", "")[:200],
                "keywords": ep.get("keywords", [])[:5],
            })

        prompt = f"""分析以下播客的成功因素和独特元素：

播客样本：
{json.dumps(sample_content, ensure_ascii=False)}

请分析：
1. 让这个播客成功的 3-5 个关键因素
2. 区别于其他播客的 3-5 个独特元素

返回 JSON 格式：
{{
  "success_factors": ["因素1", "因素2"],
  "unique_elements": ["元素1", "元素2"]
}}"""

        try:
            response = await self._call_llm(prompt)
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                fingerprint.success_factors = data.get("success_factors", [])
                fingerprint.unique_elements = data.get("unique_elements", [])
        except Exception as e:
            logger.error(f"成功因素分析失败: {e}")

        return fingerprint

    def _calculate_diversity(self, items: List[str]) -> float:
        """计算多样性分数"""
        if not items:
            return 0
        unique = set(items)
        return len(unique) / len(items)

    def compare_podcasts(
        self,
        podcast_id_1: str,
        podcast_id_2: str,
    ) -> Dict[str, Any]:
        """
        比较两个播客

        Args:
            podcast_id_1: 播客 1 ID
            podcast_id_2: 播客 2 ID

        Returns:
            比较结果
        """
        fp1 = self._fingerprints.get(podcast_id_1)
        fp2 = self._fingerprints.get(podcast_id_2)

        if not fp1 or not fp2:
            return {"error": "播客指纹不存在"}

        # 计算相似度
        vec1 = np.array(fp1.to_vector())
        vec2 = np.array(fp2.to_vector())

        # 余弦相似度
        similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

        # 特征对比
        comparison = {
            "similarity_score": float(similarity),
            "podcast_1": fp1.podcast_name,
            "podcast_2": fp2.podcast_name,
            "feature_comparison": {
                "vocabulary_richness": {
                    "podcast_1": fp1.vocabulary_richness,
                    "podcast_2": fp2.vocabulary_richness,
                },
                "formality_score": {
                    "podcast_1": fp1.formality_score,
                    "podcast_2": fp2.formality_score,
                },
                "humor_index": {
                    "podcast_1": fp1.humor_index,
                    "podcast_2": fp2.humor_index,
                },
                "depth_score": {
                    "podcast_1": fp1.depth_score,
                    "podcast_2": fp2.depth_score,
                },
            },
            "shared_success_factors": list(
                set(fp1.success_factors) & set(fp2.success_factors)
            ),
        }

        return comparison

    def find_similar_podcasts(
        self,
        podcast_id: str,
        top_k: int = 5,
    ) -> List[Dict]:
        """查找相似播客"""
        target_fp = self._fingerprints.get(podcast_id)
        if not target_fp:
            return []

        target_vec = np.array(target_fp.to_vector())

        similarities = []
        for pid, fp in self._fingerprints.items():
            if pid == podcast_id:
                continue

            vec = np.array(fp.to_vector())
            sim = np.dot(target_vec, vec) / (np.linalg.norm(target_vec) * np.linalg.norm(vec))

            similarities.append({
                "podcast_id": pid,
                "podcast_name": fp.podcast_name,
                "similarity": float(sim),
            })

        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        return similarities[:top_k]

    async def analyze_chemistry(
        self,
        episode_data: Dict,
    ) -> Dict[str, Any]:
        """
        分析主持人与嘉宾的化学反应

        Args:
            episode_data: 节目数据

        Returns:
            化学反应分析
        """
        prompt = f"""分析以下播客对话中主持人与嘉宾的互动质量：

标题：{episode_data.get('title', '')}
转录（部分）：{episode_data.get('transcript', '')[:3000]}

请评估：
1. 整体化学反应（0-10分）
2. 互动流畅度
3. 观点碰撞质量
4. 幽默互动
5. 深度探讨

返回 JSON 格式。"""

        try:
            response = await self._call_llm(prompt)
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass

        return {"chemistry_score": 7, "analysis": "分析失败"}

    def get_fingerprint(self, podcast_id: str) -> Optional[PodcastFingerprint]:
        """获取播客指纹"""
        return self._fingerprints.get(podcast_id)

    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM"""
        try:
            if self.llm_provider == "openai":
                from openai import AsyncOpenAI
                client = AsyncOpenAI()
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "你是内容分析专家。"},
                        {"role": "user", "content": prompt},
                    ],
                )
                return response.choices[0].message.content
            else:
                from anthropic import AsyncAnthropic
                client = AsyncAnthropic()
                response = await client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1500,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise
