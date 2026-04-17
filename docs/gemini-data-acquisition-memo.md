# **RESEARCH MEMORANDUM**

**TO:** Quantitative Legal Research Team

**FROM:** TEQ Empirical Evaluator

**DATE:** October 26, 2023

**SUBJECT:** Multi-Modal Strategies for Article-Level Metric Acquisition (Phase 1/2 Bridge)

## **1\. Executive Summary**

Standard web scraping of legal databases (Westlaw, HeinOnline, Lexis) often fails due to dynamic rendering and aggressive anti-bot protocols. To populate the ![][image1] formula variables—specifically ![][image2] (Novelty) and the residuals (impact vs. predicted)—we must move beyond raw scraping toward API integration, proxy repositories, and metadata harvesting.

## **2\. Proposed Acquisition Channels**

### **A. The "DOI Harvest" via Crossref API**

Instead of scraping front-end HTML, we should leverage the Digital Object Identifier (DOI) system.

* **Method:** Most top-tier law journals (Harvard, Yale, Stanford) now assign DOIs. We can query the **Crossref REST API** using the journal’s ISSN (available in our LawJournals.csv).  
* **Data Yield:** Reference counts, published dates, and "Cited-by" counts (provided by participating publishers). This bypasses the need to render complex JavaScript on journal landing pages.

### **B. SSRN "Aggregation" Protocol**

SSRN is the primary proxy for "Market Interest" (Downloads/Clicks).

* **The Problem:** Scraping individual article pages is slow and prone to bans.  
* **The Fix:** We should target the **"Journal Homepages"** or **"eJournal Collections"** on SSRN. These pages list 50–100 articles at a time in a tabular format that includes download counts in the source HTML.  
* **Formula Mapping:** Use these counts to calculate the *Market Velocity* of a title before formal citations accrue.

### **C. Digital Commons / Bepress Dashboards**

Many specialized journals (e.g., *Yale Journal on Regulation*, ranked \#1 in your Specialized\_Student\_Print file) host on the Digital Commons platform.

* **Method:** These sites often feature a "Public Dashboard" or "Readership Map." By appending /dashboards or looking for the impact\_dashboard JSON endpoint, we can often pull structured download data without ever "scraping" the visual page.

### **D. ScholarCheck & Altmetric Integration**

To measure the "Narrative Tension" (![][image3]) and "Novelty Multiplier" (![][image2]):

* **Altmetric:** Use their API (free for researchers) to track news mentions and policy document citations.  
* **Impactstory:** A tool that can pull "buzz" metrics for DOIs, allowing us to see if a high-TEQ title generated disproportionate social/news engagement compared to its peer articles in the same volume.

## **3\. Revised Operational Workflow (Phase 1.5)**

1. **Selection:** Identify a target journal volume (e.g., *Columbia Law Review* Vol 123).  
2. **Metadata Pull:** Use the Crossref API to get a list of all DOIs and titles in that volume.  
3. **W\&L Mapping:** Auto-join this list with the 2024-WL-LawJ-ALL.csv to establish the "Journal Quality" baseline (![][image4]).  
4. **Metric Enrichment:** \* Query SSRN for download counts using the title string.  
   * Query Altmetric for "Attention Scores."  
5. **TEQ Calculation:** Run the ![][image1] model and flag articles where the **Predicted Impact** (based on title) significantly diverges from **Actual Downloads** (the "Residual Analysis").

## **4\. Conclusion**

The "Jam" (Phase 2\) requires high-resolution data. By shifting from **Front-End Scraping** to **Back-End API Harvesting**, we can achieve a 90% success rate in data ingestion with minimal manual intervention.

*End of Memorandum*

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADwAAAAYCAYAAACmwZ5SAAAD0klEQVR4Xu2XXWjVZRzH95aRppJ0mBvb+Z+dLSYLzJiZE2lTFoK7cHbhlfmCXURZztDeBNuVJIKKBV3sqvTGUMZyJW6CiBCW4QRBUEyLXtbLYLLIMXGbn6/nec5+e9r0RGfpxfnCl+d5vr/v8/5y/icvL4cccsg2qqqqHq2oqHghiqImWBLGsw46qYPnMuDX8BSDeyYejzcmEokrmRDvmrBPgXaqiX9B/BvS/aSf0H4v6QlixaE/a6CTNtgDmyorK8vpfC7sojxK2swOxJy+XlpZWVkV1fJLS0una3DSSF/UTtXU1EyTrjbQN8Pb5FeFfaK9R6yPdKPVi4uLZ6BfgtdjsdjjNpYtFNH4ZSYxx4paafiX4oH+M0mhKf8uX21t7SPGlgax80xqgdVYnH1aCLjM6h74V7hF/CCM/WdoZ+hgt9Uoz1OH8LjVQQHad75A3ZqJfNR/3ueJdeN7wsSaVYe01WshdJxdu+m+sgY63lBeXl4ZaK+6FX7H6tXV1TPRd/gy+dec722vcZyfpH6X8bzv88lkcjblX2C/jq7XJwKeYflCfUrAgA9rIqz0ojBmge9ztxOrmXSStI709GRHkfhbzr8njFnoMXO+a2FsShCl7uVAnrmrEwHPH3AQnoFn4U8aKAtRH3oFYifdRJaHMYtobGG+DGNZB7vztOvsqzBmYXydXnMvbJ9eaycV6Ygro0eN2BAcJj7L15kIkVsYFm6r19Q25Y2wRb8Y1m+RqS8NOnrdTWR7GLOIUj858m0zcj7lduNRW5uU1yKQH4G9Y/Z/wr0Tt+Cv/HI85mS128ZRn89CryM/qAdzXMUUMvWNAdMRTYSH7LkwZmF8C8OY4Ha0R7/JXqP8vQZBtsBYxyGe+vjQ7m4w2lK0If8xEqVOwNF0pX/ps9AK/Rnd//7K13cvHwNuJb7XapQ/02T0KKmsXwF8HaRbXJ0WxSnvsvX0AYK2lmy+ypoE3k+tR8jUl4ZeZXUIu8OYBY3WOl/4O53HjpeiH4Qj7ossDbQS2O8G0kA7b0on/6HuHfpQONkQrn0tdl0Ys5jU5wI6aj/AgSj16op6ca/CCu9lUPXOezNKTVi+H+F1V1+vtu6pPic7bD8euirEL8Ib8Bi+d+G35C+Y61Fg7q9FIb52uDIMBMjU97+hSKcEvsxkm+FuBvexD6Lv5CMlbisIePYQa3T5JWHcI1PfAwODe4OB/Q33wk54KPS4k6AvwGdJF5N+5PSE6t/P91Ahkboqo46/cZyfCuINJn6XCfctTv4leJls4b18Dxv0j+0VeIDdSobBHHLIYVLcAfNXT53+cNGKAAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABwAAAAYCAYAAADpnJ2CAAACEklEQVR4Xu2Vz0tUURTHJSftBySoOfHmzbsz8yaJoZXvH4gKWtQiIlrNKtRskSs3KhNoRIuIiNRFESI0tGjVara1iYqIqFlHoQPqMkGEovwc5l69XBDm4VvJfOHLO+d8zz3nvvvuva+jo40DhSAIIqXUD7iq+d7NsYF+2cpdgVU3pyXkcrklBv+Cf3BTri5Ip9PH0WvwP/lvCB1yc1oGRb7Ch1IM5l1dwGo8QJvWDW+5essIw3CAYu8odFOKYV9wc4gPwQp8KjmFQmHQzWkZNLhOkVl4Xr/hsJPSSaxaLBa7eX6HDUePBz1raZbXDe/bOhMaZwnP0fAk2j9pbuuxQYHPvu8fxUxh/4WvjJbJZHyaPRFbr4Qs+cjO4LjwPK9fvp/xVXOnfrD85zTt0/acNGRyp40eG3rW94yP/RauafsaetnS6iqB7zdP0YvGx16Ut8hms56cTROXnSxxtd/vR9FvLOsx49Pwri5co2loxW9InOeoiQkYf1s2lZ7QBPbjPY8M4hWSlkulUpcVK0thCk3aucRe6PgZKzaEf5VnXVYDHmH8HfyX9lhzfzbgJtyCG/ItjQY/RlF0WBd9Bn9auevwtWiswFnepkc0NlKvzp+CC7vdEoZqnt8vxuctP8FLdk6ioPgMDR9p+xT2by6IE9hjbm4ioEEt0HevnGnVvPoq9r5IFPLLsn3ZOHLn2rE2Esc2UsmQbq8DhJUAAAAASUVORK5CYII=>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAYCAYAAADKx8xXAAAA8UlEQVR4XmNgGCFAXl7eEohPE4GPAfF+RUVFfZjG2UB8Hoi9lZWVZRUUFCSAeBeQ/x9IB6ioqIhCxeNBYjIyMiogfSxAzk0gRwjNFc+B+DNIHk38CZBiZpCTk3MFmtSJLAnka4BMBuLtyOJAwAQUOwNTlCArK6uMLAsUywBpBBpajiyurq7OCxSvRhZDAUCNK0EagYFghi6HFwA1vQTiTwwgvxALgM7ThvpvG7ocXgDUkA3VWIouhxcANawBaQQGmCm6HD7ACNT0mmT/gUIR6szd6HIYAOgkKaDCu0D8AGQTEH+H4sdAfAeIFdH1jIJBBwAt3kb5Nob7wgAAAABJRU5ErkJggg==>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAYCAYAAAAVibZIAAABpUlEQVR4Xu2UzStEYRTGZ4yvIinGZe7M3Bkzq5GNKZ9lIbtZs7BCNkrZSDaymbKykJ1CsbO0kT9ApLDHxlpSPrLD7+gdvc7MTV1Lnnp673ue5zxz7tz33lDoH37I5XK18Xi82/O8Auwo1bPZbFMqlWq3vT8ik8m0EbIBn2k+Y91kPYDr6XTaYX/K2qv7fJFMJudpeoR7sVisVWmL1J+EbKttzReY5+A7E81qTSC3jP5G+JHWKgLjuDTAba3ZQL8kfEnXy+A4TgPmO5mSB+Nq3YZMSWifrpeBsAUJhOda0yC0kyWs62Ug7ERCaVjRWmAQ+GAm7dFaIOTz+RoT+Ko1DTxFzqen6xWB+VaCo9Foo9ZKSCQSGTzHuu4L/stVM21BawZVPPF9fEN2kVo9PdPSD0dtLeS6bgviNaYr1hFbMwf+kHXSrstdmVd4UH6M9cbWP0ExLWfQTHwBl+GuBMIB7ce7Q70o14Q3s89pzxcQu+AYDRNyrXWDCPoLYf1a+A3ChN7zNUuYfURe82+OIGDKKYK34Axc46gNa08g8LGuk++rrv9xfADWI12mBynR9QAAAABJRU5ErkJggg==>