package com.toponymic.repository;

import com.toponymic.model.AnalysisInsight;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface AnalysisInsightRepository extends JpaRepository<AnalysisInsight, Long> {

    List<AnalysisInsight> findByInsightType(String insightType);

    List<AnalysisInsight> findByTitleContaining(String title);
}
