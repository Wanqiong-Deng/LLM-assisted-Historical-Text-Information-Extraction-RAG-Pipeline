import { Routes } from '@angular/router';
import { PipelineComponent } from './components/pipeline/pipeline.component';
import { ClassificationComponent } from './components/classification/classification.component';
import { AnalysisComponent } from './components/analysis/analysis.component';
import { RagChatComponent } from './components/rag-chat/rag-chat.component';

export const routes: Routes = [
  { path: '', redirectTo: '/pipeline', pathMatch: 'full' },
  { path: 'pipeline', component: PipelineComponent },
  { path: 'classification', component: ClassificationComponent },
  { path: 'analysis', component: AnalysisComponent },
  { path: 'rag-chat', component: RagChatComponent },
  { path: '**', redirectTo: '/pipeline' }
];
