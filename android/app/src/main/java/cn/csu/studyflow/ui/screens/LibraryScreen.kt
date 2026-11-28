package cn.csu.studyflow.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import cn.csu.studyflow.data.model.Scene
import cn.csu.studyflow.data.model.chunksOfDoc
import cn.csu.studyflow.ui.components.ConfidenceBadge
import cn.csu.studyflow.ui.components.SourceRefChip
import cn.csu.studyflow.ui.components.TagChip

/** ③ 资料库 + 错题本（同页双 Tab，对应 6 入口中的「资料库」「错题本」） */
@Composable
fun LibraryScreen(scene: Scene, sub: String, onSubChange: (String) -> Unit) {
    val tabs = listOf("materials" to "资料库", "mistakes" to "错题本")
    val selectedIndex = tabs.indexOfFirst { it.first == sub }.coerceAtLeast(0)

    Column {
        TabRow(selectedTabIndex = selectedIndex) {
            tabs.forEachIndexed { i, (key, label) ->
                Tab(
                    selected = i == selectedIndex,
                    onClick = { onSubChange(key) },
                    text = { Text(label) },
                )
            }
        }
        if (sub == "mistakes") {
            MistakeList(scene)
        } else {
            MaterialList(scene)
        }
    }
}

/** 资料库：doc 卡片 + 其下 chunk 行（溯源/标黄/修正都在块级，按契约） */
@Composable
private fun MaterialList(scene: Scene) {
    val correctedIds = remember { mutableStateOf(setOf<String>()) }
    LazyColumn(
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        items(scene.documents, key = { it.id }) { doc ->
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = doc.title,
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.SemiBold,
                            modifier = Modifier.weight(1f),
                        )
                        TagChip(doc.type.label)
                    }
                    Spacer(Modifier.height(4.dp))
                    Text(
                        text = "${doc.course} · ${doc.chapter}",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    val chunks = scene.chunksOfDoc(doc.id)
                    if (chunks.isNotEmpty()) {
                        Spacer(Modifier.height(6.dp))
                        HorizontalDivider()
                        chunks.forEach { c ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(top = 6.dp),
                                horizontalArrangement = Arrangement.spacedBy(6.dp),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                TagChip("知识点 ${c.kpName ?: c.kpId ?: "未挂"}")
                                if (c.page != null) SourceRefChip("P.${c.page}")
                                ConfidenceBadge(c.confidence, c.id in correctedIds.value)
                                if (c.id !in correctedIds.value && c.confidence < 0.8f) {
                                    Text(
                                        text = "修正",
                                        style = MaterialTheme.typography.labelSmall,
                                        color = MaterialTheme.colorScheme.primary,
                                        modifier = Modifier.clickable {
                                            correctedIds.value = correctedIds.value + c.id
                                        },
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

/** 错题本：严格八字段展示（契约 3.3）+ 派生 score 进度条 */
@Composable
private fun MistakeList(scene: Scene) {
    val pointNames = scene.points.associate { it.id to it.name }
    LazyColumn(
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        items(scene.mistakes, key = { it.id }) { e ->
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp)) {
                    Text(
                        text = e.questionText,
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Spacer(Modifier.height(4.dp))
                    Text(
                        text = "错答：${e.wrongAnswer}",
                        style = MaterialTheme.typography.bodySmall,
                        color = Color(0xFFB3261E),
                    )
                    Spacer(Modifier.height(6.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        TagChip("错因 · ${e.errorType}")
                        TagChip("知识点 ${pointNames[e.kpId] ?: e.kpId}")
                        TagChip("难度 ${e.difficulty}")
                        TagChip("复习 ${e.reviewCount} 次")
                        when (e.masteryStatus) {
                            "已掌握" -> TagChip(e.masteryStatus, Color(0xFFD7EFD7))
                            "模糊" -> TagChip(e.masteryStatus, Color(0xFFFFF3CD))
                            else -> TagChip(e.masteryStatus, Color(0xFFF7D8D8))
                        }
                    }
                    Spacer(Modifier.height(6.dp))
                    Text(
                        text = "首次错因：${e.firstCause}",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Spacer(Modifier.height(6.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        LinearProgressIndicator(
                            progress = { e.score },
                            modifier = Modifier.weight(1f),
                        )
                        Spacer(Modifier.padding(horizontal = 6.dp))
                        Text(
                            text = "掌握度 ${(e.score * 100).toInt()}%",
                            style = MaterialTheme.typography.labelSmall,
                        )
                    }
                }
            }
        }
    }
}
