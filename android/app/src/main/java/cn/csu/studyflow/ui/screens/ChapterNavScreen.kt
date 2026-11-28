package cn.csu.studyflow.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.VerticalDivider
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import cn.csu.studyflow.data.model.Chunk
import cn.csu.studyflow.data.model.KnowledgePoint
import cn.csu.studyflow.data.model.Scene
import cn.csu.studyflow.data.model.chunksOf
import cn.csu.studyflow.ui.components.SourceRefChip
import cn.csu.studyflow.ui.components.TagChip

/**
 * ② 章节/知识点导航：课程—章节—知识点三级组织
 * 契约对齐：章节是知识点上的字符串字段（无独立表）；知识点卡片的摘要/
 * 溯源/待确认都从 chunk 反查渲染（铁律②），不用文件夹树；
 * 平板（expanded）双栏：左章节列表 / 右知识点详情。
 */
@Composable
fun ChapterNavScreen(scene: Scene, wide: Boolean) {
    var selectedChapter by rememberSaveable { mutableStateOf(scene.chapterNames.firstOrNull() ?: "") }
    // 「可检查可修正」：已人工修正的知识点 id 集合（骨架阶段仅本页状态）
    val correctedIds = remember { mutableStateOf(setOf<String>()) }

    if (wide) {
        Row(Modifier.fillMaxWidth()) {
            ChapterList(
                chapterNames = scene.chapterNames,
                selected = selectedChapter,
                onSelect = { selectedChapter = it },
                modifier = Modifier.weight(1f),
            )
            VerticalDivider(Modifier.fillMaxHeight())
            PointDetailColumn(
                chapterTitle = selectedChapter,
                points = scene.points.filter { it.chapter == selectedChapter },
                correctedIds = correctedIds.value,
                onCorrect = { id -> correctedIds.value = correctedIds.value + id },
                chunksOf = { scene.chunksOf(it) },
                modifier = Modifier.weight(1.4f),
            )
        }
    } else {
        // 手机单栏：章节标题 + 其下知识点，全部展开
        LazyColumn(
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            scene.chapterNames.forEachIndexed { idx, ch ->
                item(key = "h-$ch") {
                    Text(
                        text = "第 ${idx + 1} 章 · $ch",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(top = 4.dp),
                    )
                }
                items(scene.points.filter { it.chapter == ch }, key = { it.id }) { p ->
                    KnowledgePointCard(
                        point = p,
                        chunks = scene.chunksOf(p.id),
                        corrected = p.id in correctedIds.value,
                        onCorrect = { correctedIds.value = correctedIds.value + p.id },
                    )
                }
            }
        }
    }
}

@Composable
private fun ChapterList(
    chapterNames: List<String>,
    selected: String,
    onSelect: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    LazyColumn(modifier = modifier, contentPadding = PaddingValues(8.dp)) {
        items(chapterNames, key = { it }) { ch ->
            val isSel = ch == selected
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onSelect(ch) }
                    .padding(horizontal = 12.dp, vertical = 10.dp),
            ) {
                Text(
                    text = ch,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = if (isSel) FontWeight.Bold else FontWeight.Normal,
                    color = if (isSel) MaterialTheme.colorScheme.primary
                    else MaterialTheme.colorScheme.onSurface,
                )
            }
        }
    }
}

@Composable
private fun PointDetailColumn(
    chapterTitle: String,
    points: List<KnowledgePoint>,
    correctedIds: Set<String>,
    onCorrect: (String) -> Unit,
    chunksOf: (String) -> List<Chunk>,
    modifier: Modifier = Modifier,
) {
    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        item {
            Text(
                text = chapterTitle,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
        }
        items(points, key = { it.id }) { p ->
            KnowledgePointCard(p, chunksOf(p.id), p.id in correctedIds, onCorrect = { onCorrect(p.id) })
        }
    }
}

/** 知识点卡片：六标签 + chunk 反查（摘要/溯源/待确认）+ 前置关联 */
@Composable
private fun KnowledgePointCard(
    point: KnowledgePoint,
    chunks: List<Chunk>,
    corrected: Boolean,
    onCorrect: () -> Unit,
) {
    val lowChunks = chunks.filter { it.confidence < 0.8f }
    val pages = chunks.mapNotNull { it.page }.distinct()
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = point.name,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.weight(1f),
                )
                if (point.mastered) {
                    TagChip("✓ 已掌握", Color(0xFFD7EFD7))
                } else {
                    TagChip("学习中", MaterialTheme.colorScheme.tertiaryContainer)
                }
            }
            Spacer(Modifier.height(6.dp))
            Text(
                text = chunks.firstOrNull()?.text ?: "（暂无关联资料块）",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(8.dp))
            Row(
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                TagChip("难度 ${point.difficulty}")
                TagChip("来源 ${point.source}")
                TagChip("版本 ${point.version}")
            }
            if (point.prereq.isNotBlank()) {
                Spacer(Modifier.height(6.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    point.prereq.split(",").filter { it.isNotBlank() }.forEach { pid ->
                        TagChip("← 前置 $pid")
                    }
                }
            }
            Spacer(Modifier.height(6.dp))
            Row(
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                if (pages.isEmpty()) {
                    TagChip("无溯源块")
                } else {
                    pages.forEach { page -> SourceRefChip("P.$page") }
                }
                if (corrected) {
                    TagChip("已人工修正", Color(0xFFD7EFD7))
                } else if (lowChunks.isNotEmpty()) {
                    TagChip("${lowChunks.size} 块待确认", Color(0xFFFFF3CD))
                    Text(
                        text = "修正",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.clickable { onCorrect() },
                    )
                }
            }
            if (point.relatedCourses.isNotBlank()) {
                Spacer(Modifier.height(6.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    point.relatedCourses.split(",").filter { it.isNotBlank() }.forEach { course ->
                        TagChip("关联课程 $course", Color(0xFFE3E0F5))
                    }
                }
            }
        }
    }
}
