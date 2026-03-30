package com.toponymic.service;

import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * Service for converting HTML source files (ctext format) to plain text.
 * Mirrors the functionality of Python's html_converter.py.
 */
@Service
public class HtmlConverterService {

    private static final Logger log = LoggerFactory.getLogger(HtmlConverterService.class);

    /**
     * Extract text content from HTML file, focusing on elements with class "ctext".
     *
     * @param htmlFile the HTML file to process
     * @return extracted text content
     */
    public String extractCtextText(File htmlFile) throws IOException {
        Document doc = Jsoup.parse(htmlFile, "UTF-8");
        Elements ctextElements = doc.select("td.ctext");

        List<String> lines = new ArrayList<>();
        for (Element el : ctextElements) {
            String text = el.text().trim();
            if (!text.isEmpty()) {
                lines.add(text);
            }
        }

        return String.join("\n", lines);
    }

    /**
     * Convert all HTML files in inputDir to text files in outputDir.
     *
     * @param inputDir  directory containing HTML files
     * @param outputDir directory to write text files
     * @return number of files converted
     */
    public int convertAll(Path inputDir, Path outputDir) throws IOException {
        if (!Files.exists(outputDir)) {
            Files.createDirectories(outputDir);
        }

        File[] htmlFiles = inputDir.toFile().listFiles(
            (dir, name) -> name.toLowerCase().endsWith(".html") || name.toLowerCase().endsWith(".htm")
        );

        if (htmlFiles == null || htmlFiles.length == 0) {
            log.warn("No HTML files found in {}", inputDir);
            return 0;
        }

        int count = 0;
        for (File htmlFile : htmlFiles) {
            try {
                String text = extractCtextText(htmlFile);
                String outputName = htmlFile.getName().replaceAll("\\.(html|htm)$", ".txt");
                Path outputFile = outputDir.resolve(outputName);
                Files.writeString(outputFile, text);
                log.info("Converted: {} -> {}", htmlFile.getName(), outputName);
                count++;
            } catch (IOException e) {
                log.error("Failed to convert {}: {}", htmlFile.getName(), e.getMessage());
            }
        }

        log.info("Converted {}/{} HTML files", count, htmlFiles.length);
        return count;
    }
}
