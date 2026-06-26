# Idempotens-audit -- atomara vs sarbara skrivningar

_Genererad 2026-06-26 22:48 av idempotens_audit.py. Utvecklare: Jens Palmo._

Skannade `C:\Projekt\BCG`. Hittade **164** skrivnings-anrop: **0** atomara, **164** sarbara.

## Vad detta betyder
En SARBAR skrivning gar direkt till slutmalet. Kraschar processen mitt i (natfel, token-dod E.3, VM-glapp) lamnas en HALV slutfil som nasta steg laser som trunkerad data -> tyst fel (dyraste felklassen). En ATOMAR skrivning gar till temp och byter namn nar klart -> en krasch lamnar bara ofarlig temp-skrap.

## SARBARA skrivningar (atgarda -- prioritera de som skriver pipeline-artefakter)

| Anrop | Fil | Rad | Kontext |
|-------|-----|-----|---------|
| `write_text` | idempotens_audit.py | 176 | `out.write_text("\n".join(L), encoding="utf-8")` |
| `to_excel` | compare_elasticity_runs.py | 292 | `summary.to_excel(writer, sheet_name="Summary", index=False)` |
| `to_excel` | compare_elasticity_runs.py | 293 | `joined.to_excel(writer, sheet_name="Joined_comparison", index=False)` |
| `to_excel` | compare_elasticity_runs.py | 294 | `significant_only.to_excel(writer, sheet_name="Significant_only", index=False)` |
| `save` | xlsx_export_bcg_freshness.py | 253 | `wb.save(out_path)` |
| `save` | validate_orchestrator_vs_facit.py | 176 | `wb.save(fn)` |
| `to_json` | blob.py | 151 | `data = rs.to_json().encode("utf-8")` |
| `to_json` | run_status.py | 508 | `s = rs.to_json()` |
| `to_json` | run_status.py | 515 | `rs3 = RunStatus.from_json(rs.to_json())` |
| `to_json` | app.py | 111 | `return app.response_class(rs.to_json(), mimetype="application/json")` |
| `savefig` | Clustering.py | 32 | `plt.savefig(file_path, bbox_inches="tight")` |
| `to_csv` | Clustering.py | 62 | `row_sdf_kmeans.to_csv(clustering_metrics_file_path, index=False)` |
| `to_csv` | Clustering.py | 71 | `scaler_params.reset_index().to_csv(scalar_params_file_path,index=False)` |
| `to_csv` | Clustering.py | 72 | `centroid.reset_index().to_csv(centroid_file_path,index=False)` |
| `to_csv` | Clustering.py | 124 | `final.to_csv(clustering_var_file_path,index=False)` |
| `to_csv` | Clustering.py | 191 | `final.to_csv(profiling_var_file_path,index=False)` |
| `to_csv` | Clustering.py | 201 | `full_data.to_csv(data_in_scope_var_file_path,index=False)` |
| `to_csv` | Data_Preparation.py | 97 | `overall_df.to_csv(overall_median_output_file_path, index=False)` |
| `to_csv` | Data_Preparation.py | 101 | `median_df.to_csv(region_median_output_file_path, index=False)` |
| `to_csv` | Data_Preparation.py | 105 | `bounds_df.to_csv(bounds_file_path, index = False)` |
| `to_csv` | Data_Preparation.py | 109 | `df.to_csv(preprocessed_file_path, index=False)` |
| `save` | Overwrite_Excel.py | 62 | `wb.save()` |
| `to_excel` | Sweden_Productive_Time_Data_Creation.py | 499 | `df_interpolated_3.to_excel(output_file, index=False)` |
| `to_csv` | data_prepration.py | 119 | `df.to_csv(path, index=False)` |
| `to_excel` | data_prepration.py | 259 | `df_dates.to_excel('holiday_check0820.xlsx', index = False)` |
| `to_csv` | data_prepration.py | 68 | `trasform_control.to_csv(file, index=False)` |
| `to_excel` | data_prep_after_model_output.py | 335 | `sign_summary.to_excel(rf".\output\significant_variable_summary_{itr}.xlsx", index=False)` |
| `to_excel` | data_prep_after_model_output.py | 340 | `model_result_1_final.to_excel(r".\output\model_result_summary_ready.xlsx", index=False)` |
| `to_excel` | data_prep_after_model_output.py | 341 | `model_output_final.to_excel(r".\output\output_summary_ready.xlsx", index=False)` |
| `to_excel` | data_prep_after_model_output.py | 342 | `final_model_df.to_excel(r".\output\final_model_cluster_granularity.xlsx", index=False)` |
| `save` | data_prep_after_model_output.py | 297 | `wb.save()  # keeps existing format (.xlsb or .xlsx)` |
| `save` | data_prep_after_model_output.py | 267 | `wb.save(str(file_path))` |
| `to_excel` | excel_creation.py | 121 | `raw_data.to_excel(raw_data_output_path, index=False)` |
| `to_excel` | excel_creation.py | 132 | `model_summary.to_excel(model_summary_path_output, index=False)` |
| `to_excel` | excel_creation.py | 158 | `output_summary.to_excel(output_summary_path_output, index=False)` |
| `save` | excel_creation.py | 73 | `wb.save()  # keeps existing format (.xlsb or .xlsx)` |
| `save` | excel_creation.py | 43 | `wb.save(str(file_path))` |
| `to_excel` | feature_selection.py | 408 | `result_df.to_excel(f"{summary_path}All_combinations.xlsx", index=False)` |
| `to_csv` | feature_selection.py | 572 | `df.to_csv(file, index=False)` |
| `to_excel` | feature_selection.py | 590 | `df.to_excel(file, index=False)` |
| `to_excel` | feature_selection.py | 158 | `control_file.to_excel(file, index=False)` |
| `to_excel` | feature_selection.py | 340 | `model_group_result.to_excel(f"{summary_path}{mg}_All_itrs.xlsx", index=False)` |
| `to_excel` | feature_selection.py | 345 | `model_group_result.to_excel(f"{summary_path}{mg[:30]}_All_itrs.xlsx", index=False)` |
| `to_csv` | model.py | 337 | `df.to_csv(file, index=False)` |
| `to_excel` | model.py | 355 | `df.to_excel(file, index=False)` |
| `to_excel` | model.py | 93 | `control_file.to_excel(file, index=False)` |
| `to_excel` | model.py | 223 | `df_.to_excel(writer, 'sheet%s' % n, index=False)` |
| `to_excel` | model.py | 225 | `df_.to_excel(writer, 'sheet%s' % n)` |
| `to_csv` | regular_price.py | 122 | `df.to_csv(path, index=False)` |
| `to_csv` | data_prepration.py | 121 | `df.to_csv(path, index=False)` |
| `to_excel` | data_prepration.py | 262 | `df_dates.to_excel('holiday_check0820.xlsx', index = False)` |
| `to_csv` | data_prepration.py | 69 | `trasform_control.to_csv(file, index=False)` |
| `to_csv` | data_prep_after_model_output.py | 65 | `df.to_csv(rf".\output\rank_{itr}.csv", index=False)` |
| `to_excel` | data_prep_after_model_output.py | 301 | `model_result_1.to_excel(rf".\output\model_result_summary_ready_{itr}.xlsx", index=False)` |
| `to_excel` | data_prep_after_model_output.py | 302 | `model_out.to_excel(rf".\output\output_summary_ready_{itr}.xlsx", index=False)` |
| `to_excel` | data_prep_after_model_output.py | 306 | `sign_summary.to_excel(rf".\output\significant_variable_summary_{itr}.xlsx", index=False)` |
| `save` | data_prep_after_model_output.py | 263 | `wb.save()  # keeps existing format (.xlsb or .xlsx)` |
| `save` | data_prep_after_model_output.py | 233 | `wb.save(str(file_path))` |
| `to_excel` | feature_selection.py | 405 | `result_df.to_excel(f"{summary_path}All_combinations.xlsx", index=False)` |
| `to_csv` | feature_selection.py | 569 | `df.to_csv(file, index=False)` |
| `to_excel` | feature_selection.py | 588 | `df.to_excel(file, index=False)` |
| `to_excel` | feature_selection.py | 155 | `control_file.to_excel(file, index=False)` |
| `to_excel` | feature_selection.py | 337 | `model_group_result.to_excel(f"{summary_path}{mg}_All_itrs.xlsx", index=False)` |
| `to_excel` | feature_selection.py | 342 | `model_group_result.to_excel(f"{summary_path}{mg[:30]}_All_itrs.xlsx", index=False)` |
| `to_csv` | model.py | 338 | `df.to_csv(file, index=False)` |
| `to_excel` | model.py | 356 | `df.to_excel(file, index=False)` |
| `to_excel` | model.py | 94 | `control_file.to_excel(file, index=False)` |
| `to_excel` | model.py | 224 | `df_.to_excel(writer, 'sheet%s' % n, index=False)` |
| `to_excel` | model.py | 226 | `df_.to_excel(writer, 'sheet%s' % n)` |
| `to_csv` | regular_price.py | 121 | `df.to_csv(path, index=False)` |
| `to_csv` | 2.Sweden_Bundle_Clinic_Model_Data_Creation.py | 57 | `bundle_data_final_all.to_csv(output_data, index=False)` |
| `to_csv` | data_prepration.py | 120 | `df.to_csv(path, index=False)` |
| `to_excel` | data_prepration.py | 261 | `df_dates.to_excel('holiday_check0820.xlsx', index = False)` |
| `to_csv` | data_prepration.py | 68 | `trasform_control.to_csv(file, index=False)` |
| `to_csv` | data_prep_after_model_output.py | 65 | `df.to_csv(rf".\output\rank_{config['itr_name']}.csv", index=False)` |
| `to_excel` | data_prep_after_model_output.py | 317 | `model_result_1.to_excel(rf".\output\model_result_summary_ready_{itr}.xlsx", index=False)` |
| `to_excel` | data_prep_after_model_output.py | 318 | `model_out.to_excel(rf".\output\output_summary_ready_{itr}.xlsx", index=False)` |
| `to_excel` | data_prep_after_model_output.py | 322 | `sign_summary.to_excel(rf".\output\significant_variable_summary_{itr}.xlsx", index=False)` |
| `save` | data_prep_after_model_output.py | 275 | `wb.save()  # keeps existing format (.xlsb or .xlsx)` |
| `save` | data_prep_after_model_output.py | 245 | `wb.save(str(file_path))` |
| `to_excel` | feature_selection.py | 406 | `result_df.to_excel(f"{summary_path}All_combinations.xlsx", index=False)` |
| `to_csv` | feature_selection.py | 575 | `df.to_csv(file, index=False)` |
| `to_excel` | feature_selection.py | 593 | `df.to_excel(file, index=False)` |
| `to_excel` | feature_selection.py | 156 | `control_file.to_excel(file, index=False)` |
| `to_excel` | feature_selection.py | 338 | `model_group_result.to_excel(f"{summary_path}{mg}_All_itrs.xlsx", index=False)` |
| `to_excel` | feature_selection.py | 343 | `model_group_result.to_excel(f"{summary_path}{mg[:30]}_All_itrs.xlsx", index=False)` |
| `to_csv` | model.py | 337 | `df.to_csv(file, index=False)` |
| `to_excel` | model.py | 356 | `df.to_excel(file, index=False)` |
| `to_excel` | model.py | 93 | `control_file.to_excel(file, index=False)` |
| `to_excel` | model.py | 223 | `df_.to_excel(writer, 'sheet%s' % n, index=False)` |
| `to_excel` | model.py | 225 | `df_.to_excel(writer, 'sheet%s' % n)` |
| `to_csv` | regular_price.py | 120 | `df.to_csv(path, index=False)` |
| `to_excel` | Fall_Back_Logic.py | 639 | `dff_blended_agg.to_excel(dff_blended_agg_file_name_path, index=False, engine="openpyxl")` |
| `to_excel` | Fall_Back_Logic.py | 677 | `dv8.to_excel("Final_Fallback_Data.xlsx", index=False, engine="openpyxl")` |
| `to_csv` | Fall_Back_Logic.py | 684 | `dfsite_temp.sort_values('SigSites_Sum', ascending=False).to_csv(product_site_summ_file_nam` |
| `to_excel` | Fall_Back_Logic.py | 686 | `dv8.to_excel(output_file_path, index=False, engine="openpyxl")` |
| `save` | Fall_Back_Logic.py | 614 | `wb.save()  # keeps existing format (.xlsb or .xlsx)` |
| `save` | Fall_Back_Logic.py | 584 | `wb.save(str(file_path))` |
| `save` | bundle_csv_to_xlsx.py | 124 | `wb.save(xlsx_path)` |
| `write_bytes` | fix_bundle_maj_status.py | 91 | `(bdir / f"{RUN_ID}.json").write_bytes(raw)` |
| `write_bytes` | fix_cluster_maj_status.py | 121 | `(bdir / f"{RUN_ID}.json").write_bytes(raw)` |
| `write_text` | patch_bundle_constants_g7.py | 157 | `p.write_text(new_txt, encoding="utf-8")` |
| `write_text` | patch_bundle_yearflag.py | 109 | `SQL.write_text(new_text, encoding="utf-8")` |
| `write_text` | patch_bundle_yearflag.py | 104 | `BAK.write_text(text, encoding="utf-8")` |
| `write_text` | patch_runners_after_validation.py | 141 | `p.write_text(text, encoding="utf-8")   # utf-8, ingen BOM` |
| `save` | run_cluster_maj_diagnosis.py | 106 | `wb.save(fp)` |
| `write_text` | conservation.py | 267 | `SNAPSHOT.write_text(json.dumps(cur_snap, indent=2, ensure_ascii=False), encoding="utf-8")` |
| `to_excel` | prefilter_unpriced.py | 131 | `clean.to_excel(out, index=False, engine="openpyxl")` |
| `write_text` | run_smoke_facit.py | 197 | `REFERENCE.write_text(json.dumps(cur, indent=2, ensure_ascii=False), encoding="utf-8")` |
| `save` | valve_map.py | 380 | `wb.save(out)` |
| `write_text` | valve_map.py | 339 | `out.write_text("\n".join(L), encoding="utf-8")` |
| `save` | _validation_helpers.py | 222 | `wb.save(receipt_path)` |
| `save` | all_chain_validator.py | 755 | `wb.save(out)` |
| `write_text` | all_chain_validator.py | 712 | `out.write_text("\n".join(L), encoding="utf-8")` |
| `save` | bundle_chain_validator.py | 487 | `wb.save(out)` |
| `save` | delivery_probe.py | 219 | `wb.save(fp); return fp` |
| `save` | structure_probe.py | 411 | `wb.save(fp)` |
| `save` | value_probe.py | 149 | `wb.save(fp); log(f"\n[Saved] {fp}")` |
| `save` | run_all.py | 153 | `wb.save(out)` |
| `save` | build_r12_for_model.py | 277 | `wb.save(out_path)` |
| `to_csv` | fallback_blend.py | 307 | `blended.to_csv(out, index=False, encoding="cp1252", errors="replace")` |
| `to_csv` | fallback_blend.py | 310 | `final_model.to_csv(fm_out, index=False, encoding="cp1252", errors="replace")` |
| `to_excel` | run_step6.py | 86 | `df.to_excel(p["dest"], index=False, engine="openpyxl")` |
| `to_csv` | data_prepration.py | 119 | `df.to_csv(path, index=False)` |
| `to_excel` | data_prepration.py | 259 | `df_dates.to_excel('holiday_check0820.xlsx', index = False)` |
| `to_csv` | data_prepration.py | 68 | `trasform_control.to_csv(file, index=False)` |
| `to_excel` | data_prep_after_model_output.py | 335 | `sign_summary.to_excel(rf".\output\significant_variable_summary_{itr}.xlsx", index=False)` |
| `to_excel` | data_prep_after_model_output.py | 340 | `model_result_1_final.to_excel(r".\output\model_result_summary_ready.xlsx", index=False)` |
| `to_excel` | data_prep_after_model_output.py | 341 | `model_output_final.to_excel(r".\output\output_summary_ready.xlsx", index=False)` |
| `to_excel` | data_prep_after_model_output.py | 342 | `final_model_df.to_excel(r".\output\final_model_cluster_granularity.xlsx", index=False)` |
| `save` | data_prep_after_model_output.py | 297 | `wb.save()  # keeps existing format (.xlsb or .xlsx)` |
| `save` | data_prep_after_model_output.py | 267 | `wb.save(str(file_path))` |
| `to_excel` | excel_creation.py | 121 | `raw_data.to_excel(raw_data_output_path, index=False)` |
| `to_excel` | excel_creation.py | 132 | `model_summary.to_excel(model_summary_path_output, index=False)` |
| `to_excel` | excel_creation.py | 158 | `output_summary.to_excel(output_summary_path_output, index=False)` |
| `save` | excel_creation.py | 73 | `wb.save()  # keeps existing format (.xlsb or .xlsx)` |
| `save` | excel_creation.py | 43 | `wb.save(str(file_path))` |
| `to_excel` | feature_selection.py | 408 | `result_df.to_excel(f"{summary_path}All_combinations.xlsx", index=False)` |
| `to_csv` | feature_selection.py | 572 | `df.to_csv(file, index=False)` |
| `to_excel` | feature_selection.py | 590 | `df.to_excel(file, index=False)` |
| `to_excel` | feature_selection.py | 158 | `control_file.to_excel(file, index=False)` |
| `to_excel` | feature_selection.py | 340 | `model_group_result.to_excel(f"{summary_path}{mg}_All_itrs.xlsx", index=False)` |
| `to_excel` | feature_selection.py | 345 | `model_group_result.to_excel(f"{summary_path}{mg[:30]}_All_itrs.xlsx", index=False)` |
| `to_csv` | model.py | 337 | `df.to_csv(file, index=False)` |
| `to_excel` | model.py | 355 | `df.to_excel(file, index=False)` |
| `to_excel` | model.py | 93 | `control_file.to_excel(file, index=False)` |
| `to_excel` | model.py | 223 | `df_.to_excel(writer, 'sheet%s' % n, index=False)` |
| `to_excel` | model.py | 225 | `df_.to_excel(writer, 'sheet%s' % n)` |
| `to_csv` | regular_price.py | 122 | `df.to_csv(path, index=False)` |
| `to_csv` | data_prepration.py | 119 | `df.to_csv(path, index=False)` |
| `to_excel` | data_prepration.py | 259 | `df_dates.to_excel('holiday_check0820.xlsx', index = False)` |
| `to_csv` | data_prepration.py | 68 | `trasform_control.to_csv(file, index=False)` |
| `to_csv` | model.py | 337 | `df.to_csv(file, index=False)` |
| `to_excel` | model.py | 355 | `df.to_excel(file, index=False)` |
| `to_excel` | model.py | 93 | `control_file.to_excel(file, index=False)` |
| `to_excel` | model.py | 223 | `df_.to_excel(writer, 'sheet%s' % n, index=False)` |
| `to_excel` | model.py | 225 | `df_.to_excel(writer, 'sheet%s' % n)` |
| `to_csv` | regular_price.py | 122 | `df.to_csv(path, index=False)` |
| `to_excel` | Fall_Back_Logic.py | 642 | `dff_blended_agg.to_excel(dff_blended_agg_file_name_path, index=False, engine="openpyxl")` |
| `to_excel` | Fall_Back_Logic.py | 680 | `dv8.to_excel("Final_Fallback_Data.xlsx", index=False, engine="openpyxl")` |
| `to_csv` | Fall_Back_Logic.py | 687 | `dfsite_temp.sort_values('SigSites_Sum', ascending=False).to_csv(product_site_summ_file_nam` |
| `to_excel` | Fall_Back_Logic.py | 689 | `dv8.to_excel(output_file_path, index=False, engine="openpyxl")` |
| `save` | Fall_Back_Logic.py | 617 | `wb.save()  # keeps existing format (.xlsb or .xlsx)` |
| `save` | Fall_Back_Logic.py | 587 | `wb.save(str(file_path))` |

**Atgard:** ersatt `df.to_X(slutmal)` med write-rename-monster (skriv till `.tmp.<pid>`, sedan `os.replace(tmp, slutmal)`). Se KARN-principen om atomara skrivningar.

## Begransningar (arlig mätning)
- Heuristisk: 'atomar' = skriver till temp + rename inom 6 rader. Ett anrop som delar upp temp/rename langre isar kan felklassas som sarbart -- verifiera manuellt.
- Tackningen ar statisk (AST): fangar direkta `.to_X()`-anrop, ej skrivningar via wrappers/bibliotek som doljer anropet. Komplettera med blick pa egna I/O-helpers.
- En sarbar skrivning till en ENGANGS-fil (ej pipeline-artefakt) ar lagprioriterad.