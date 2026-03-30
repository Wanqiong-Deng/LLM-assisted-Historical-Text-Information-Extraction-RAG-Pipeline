package com.toponymic.repository;

import com.toponymic.model.ClassificationResult;
import com.toponymic.model.ClassificationResult.ClassificationType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ClassificationResultRepository extends JpaRepository<ClassificationResult, Long> {

    List<ClassificationResult> findByClassification(ClassificationType classification);

    List<ClassificationResult> findByClassificationMethod(String method);

    @Query("SELECT c.classification, COUNT(c) FROM ClassificationResult c GROUP BY c.classification")
    List<Object[]> countByClassification();

    @Query("SELECT c FROM ClassificationResult c WHERE c.placenameRecord.placename LIKE %:placename%")
    List<ClassificationResult> findByPlacenameContaining(String placename);

    @Query("SELECT c FROM ClassificationResult c WHERE c.placenameRecord.contextText LIKE %:keyword%")
    List<ClassificationResult> searchByKeyword(String keyword);

    long countByClassification(ClassificationType classification);
}
