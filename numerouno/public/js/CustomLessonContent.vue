<template>
  <div v-if="youtube">
    <iframe
      class="youtube-video"
      :src="getYouTubeVideoSource(youtube.split('/').pop())"
      width="100%"
      :height="screenSize.width < 640 ? 200 : 400"
      frameborder="0"
      allowfullscreen
    ></iframe>
  </div>
  <div v-for="block in content?.split('\n\n')">
    <div v-if="block.includes('{{ YouTubeVideo}}')">
      <iframe
        class="youtube-video"
        :src="getYouTubeVideoSource(block)"
        width="100%"
        :height="screenSize.width < 640 ? 200 : 400"
        frameborder="0"
        allowfullscreen
      ></iframe>
    </div>
    <!-- Only show Quiz if canShowQuiz is true -->
    <div v-else-if="block.includes('{{ Quiz }}') && canShowQuiz">
      <Quiz :quiz="getId(block)" />
    </div>
    <!-- ... other blocks ... -->
    <div v-else v-html="markdown.render(block)"></div>
  </div>
  <div v-if="quizId && canShowQuiz">
    <Quiz :quiz="quizId" />
  </div>
</template>

<script setup>
import Quiz from '@/components/QuizBlock.vue'
import MarkdownIt from 'markdown-it'
import { useScreenSize } from '@/utils/composables'
import { ref, onMounted } from 'vue'

const screenSize = useScreenSize()
const markdown = new MarkdownIt({ html: true, linkify: true })

const props = defineProps({
  content: { type: String, required: true },
  youtube: { type: String, required: false },
  quizId: { type: String, required: false },
})

const getYouTubeVideoSource = (block) => {
  if (block.includes('{{')) block = getId(block)
  return `https://www.youtube.com/embed/${block}`
}
const getId = (block) => block.match(/\(["']([^"']+?)["']\)/)[1]

const canShowQuiz = ref(true)

onMounted(async () => {
  if (props.quizId) {
    // Call your custom backend API
    const res = await window.frappe.call('numerouno.api.can_show_quiz', {
      quiz_id: props.quizId
    })
    canShowQuiz.value = res.message
  }
})
</script>
