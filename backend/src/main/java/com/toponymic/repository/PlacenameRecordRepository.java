package com.toponymic.repository;

import com.toponymic.model.PlacenameRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface PlacenameRecordRepository extends JpaRepository<PlacenameRecord, Long> {

    List<PlacenameRecord> findBySourceFile(String sourceFile);

    List<PlacenameRecord> findByPlacenameContaining(String placename);

    @Query("SELECT DISTINCT p.sourceFile FROM PlacenameRecord p")
    List<String> findDistinctSourceFiles();

    long countBySourceFile(String sourceFile);
}
