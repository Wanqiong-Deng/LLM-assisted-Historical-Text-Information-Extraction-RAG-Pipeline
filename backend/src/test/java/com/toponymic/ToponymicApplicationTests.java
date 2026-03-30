package com.toponymic;

import com.toponymic.model.PlacenameRecord;
import com.toponymic.repository.PlacenameRecordRepository;
import com.toponymic.service.PlacenameExtractorService;
import com.toponymic.service.LlmClassifierService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@ActiveProfiles("test")
class ToponymicApplicationTests {

    @Autowired
    private PlacenameExtractorService extractorService;

    @Autowired
    private LlmClassifierService classifierService;

    @Autowired
    private PlacenameRecordRepository repository;

    @Test
    void contextLoads() {
        assertThat(extractorService).isNotNull();
        assertThat(classifierService).isNotNull();
    }

    @Test
    void testExtractValidPlacename() {
        assertThat(extractorService.extractValidPlacename("青山縣，東距郡城百里")).isEqualTo("青山縣");
        assertThat(extractorService.extractValidPlacename("因山名之")).isNull();
        assertThat(extractorService.extractValidPlacename("洞庭湖，廣三千里")).isEqualTo("洞庭湖");
    }

    @Test
    void testCleanLineStart() {
        assertThat(extractorService.cleanLineStart("漢青山縣")).isEqualTo("青山縣");
        assertThat(extractorService.cleanLineStart("唐長安州")).isEqualTo("長安州");
    }

    @Test
    void testRegexStrongPattern() {
        assertThat(classifierService.checkStrongByRegex("因山名之，故置此縣")).isNotNull();
        assertThat(classifierService.checkStrongByRegex("《水經注》云：此地...")).isNull();
        assertThat(classifierService.checkStrongByRegex("縣東南五十里")).isNull();
    }

    @Test
    void testSaveAndRetrieveRecord() {
        PlacenameRecord record = new PlacenameRecord("測試縣", "因水名之", "test.html");
        PlacenameRecord saved = repository.save(record);
        assertThat(saved.getId()).isNotNull();

        List<PlacenameRecord> found = repository.findByPlacenameContaining("測試");
        assertThat(found).isNotEmpty();
    }
}
