package com.toponymic.service;

import com.toponymic.config.AppConfig;
import com.toponymic.model.PlacenameRecord;
import com.toponymic.repository.PlacenameRecordRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * Service for extracting place names from Classical Chinese text.
 * Mirrors the functionality of Python's placename_extractor.py.
 */
@Service
public class PlacenameExtractorService {

    private static final Logger log = LoggerFactory.getLogger(PlacenameExtractorService.class);

    // Admin level prefixes to remove when extracting clean placenames
    private static final List<String> ADMIN_LEVELS = List.of(
        "縣", "州", "郡", "府", "道", "路", "省"
    );

    private static final int MAX_CONTEXT_CHARS = 200;

    @Autowired
    private PlacenameRecordRepository repository;

    /**
     * Extract placename records from a text file and save to SQL database.
     *
     * @param textFile  path to the input text file
     * @param sourceFile label for the source (filename)
     * @return list of saved PlacenameRecord entities
     */
    public List<PlacenameRecord> extractFromFile(Path textFile, String sourceFile) throws IOException {
        List<String> lines = Files.readAllLines(textFile);
        List<PlacenameRecord> records = new ArrayList<>();

        for (int i = 0; i < lines.size(); i++) {
            String line = lines.get(i).trim();
            if (line.isEmpty()) continue;

            String placename = extractValidPlacename(line);
            if (placename == null) continue;

            // Build context window (current line + next lines if needed)
            String context = buildContext(lines, i, MAX_CONTEXT_CHARS);

            PlacenameRecord record = new PlacenameRecord(placename, context, sourceFile);
            record.setLineNumber(i + 1);
            records.add(record);
        }

        List<PlacenameRecord> saved = repository.saveAll(records);
        log.info("Extracted and saved {} placename records from {}", saved.size(), sourceFile);
        return saved;
    }

    /**
     * Attempt to extract a valid placename from a line of text.
     * Returns null if no valid placename is found.
     */
    public String extractValidPlacename(String line) {
        String cleaned = cleanLineStart(line);
        if (cleaned.isEmpty()) return null;

        for (String suffix : AppConfig.PLACE_SUFFIXES) {
            // Look for characters immediately before the suffix
            Pattern pattern = Pattern.compile("([\\u4e00-\\u9fff]{1,4}" + suffix + ")");
            Matcher matcher = pattern.matcher(cleaned);
            if (matcher.find()) {
                return matcher.group(1);
            }
        }
        return null;
    }

    /**
     * Clean line start by removing dynasty prefixes and admin level markers.
     */
    public String cleanLineStart(String line) {
        String result = line.trim();

        // Remove leading dynasty names
        for (String dynasty : AppConfig.DYNASTY_PREFIXES) {
            if (result.startsWith(dynasty)) {
                result = result.substring(dynasty.length()).trim();
                break;
            }
        }

        // Remove leading admin level markers like "縣：" "州："
        for (String level : ADMIN_LEVELS) {
            if (result.startsWith(level)) {
                result = result.substring(level.length()).trim();
                if (result.startsWith("：") || result.startsWith(":")) {
                    result = result.substring(1).trim();
                }
                break;
            }
        }

        return result;
    }

    private String buildContext(List<String> lines, int startIndex, int maxChars) {
        StringBuilder sb = new StringBuilder();
        for (int i = startIndex; i < lines.size() && sb.length() < maxChars; i++) {
            if (!sb.isEmpty()) sb.append(" ");
            sb.append(lines.get(i).trim());
        }
        return sb.length() > maxChars ? sb.substring(0, maxChars) : sb.toString();
    }

    /**
     * Get all records from the database.
     */
    public List<PlacenameRecord> getAllRecords() {
        return repository.findAll();
    }

    /**
     * Search records by placename.
     */
    public List<PlacenameRecord> searchByPlacename(String placename) {
        return repository.findByPlacenameContaining(placename);
    }

    /**
     * Get statistics about extracted records.
     */
    public Map<String, Object> getStats() {
        Map<String, Object> stats = new LinkedHashMap<>();
        stats.put("totalRecords", repository.count());
        stats.put("sourceFiles", repository.findDistinctSourceFiles());
        return stats;
    }
}
