from pathlib import Path
import unittest

from paper_parser import TextChunk, build_context_bundle, chunk_pdf_text, select_chunks


class ChunkingTests(unittest.TestCase):
    def test_chunking_preserves_pdf_page_numbers(self) -> None:
        chunks = chunk_pdf_text("first\x00 page\fsecond page", max_chars=500)
        self.assertEqual([(chunk.page, chunk.text) for chunk in chunks], [
            (1, "first page"),
            (2, "second page"),
        ])

    def test_retrieval_keeps_first_chunk_and_relevant_evidence(self) -> None:
        chunks = [
            TextChunk(0, 1, "abstract"),
            TextChunk(1, 2, "unrelated appendix"),
            TextChunk(2, 3, "agent mutation Pareto search"),
        ]
        selected = select_chunks(chunks, "agent mutation", top_k=2)
        self.assertEqual([chunk.index for chunk in selected], [0, 2])


class ContextBundleTests(unittest.TestCase):
    def test_bundle_contains_template_query_and_page_locator(self) -> None:
        bundle = build_context_bundle(
            pdf_path=Path("paper.pdf"),
            query="NAS budget",
            template="# Template",
            chunks=[TextChunk(4, 7, "reported result")],
        )
        self.assertIn("# Template", bundle)
        self.assertIn("NAS budget", bundle)
        self.assertIn("PDF page 7", bundle)
        self.assertIn("reported result", bundle)


if __name__ == "__main__":
    unittest.main()
