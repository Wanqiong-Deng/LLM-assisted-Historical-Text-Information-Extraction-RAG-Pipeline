package com.toponymic.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.util.List;

@Configuration
public class AppConfig implements WebMvcConfigurer {

    @Value("${llm.api.key}")
    private String apiKey;

    @Value("${llm.api.base-url}")
    private String apiBaseUrl;

    @Value("${llm.classification.model}")
    private String classificationModel;

    @Value("${llm.rag.model}")
    private String ragModel;

    @Value("${llm.embedding.model}")
    private String embeddingModel;

    @Value("${llm.api.call-interval-ms:600}")
    private long apiCallIntervalMs;

    @Value("${pipeline.save-frequency:5}")
    private int saveFrequency;

    // Regex patterns for STRONG classification (causal naming language in Classical Chinese)
    public static final List<String> STRONG_PATTERNS = List.of(
        "因.*?名之",
        "因.*?為名",
        "因.*?得名",
        "故名.*?焉",
        "故名.*?也",
        "故名",
        "取.*?之義",
        "以.*?名之",
        "以.*?為名"
    );

    // Place suffixes to identify toponyms
    public static final List<String> PLACE_SUFFIXES = List.of(
        "縣", "州", "郡", "鄉", "鎮", "村", "山", "水", "江",
        "河", "湖", "海", "峰", "嶺", "谷", "洞", "泉", "潭"
    );

    // Dynasty prefixes to clean from text
    public static final List<String> DYNASTY_PREFIXES = List.of(
        "漢", "唐", "宋", "元", "明", "清", "周", "秦", "晉",
        "隋", "魏", "吳", "蜀", "齊", "梁", "陳"
    );

    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
            .allowedOrigins("http://localhost:4200")
            .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
            .allowedHeaders("*");
    }

    public String getApiKey() { return apiKey; }
    public String getApiBaseUrl() { return apiBaseUrl; }
    public String getClassificationModel() { return classificationModel; }
    public String getRagModel() { return ragModel; }
    public String getEmbeddingModel() { return embeddingModel; }
    public long getApiCallIntervalMs() { return apiCallIntervalMs; }
    public int getSaveFrequency() { return saveFrequency; }
}
