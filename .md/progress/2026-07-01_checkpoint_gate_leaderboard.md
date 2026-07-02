# Checkpoint Gate Leaderboard

Date: 2026-07-01

Role: GPU 2 checkpoint evaluator/watchdog. This file is evaluation-only; no training is performed here.

Accepted checkpoint: none
Accepted adapter: none
Consecutive bad Stage 2A checkpoints: 4

## Leaderboard

| Status | Candidate | Adapter | AIHub CER | AIHub Exact | KORIE CER | KORIE WER | KORIE Exact | Rep Loop | Avg Gen Len | Target Avg Len | Len Ratio | Control Count |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rejected | stage2a_checkpoint-100 | `<PROJECT_ROOT>/runs/kept_checkpoints/stage2a_aihub91_region_50k_from_stage1_50k_v3_bs16_ga2_512_20260701T0745Z/checkpoint-100` | 1.0000 | 0.00% | 1.0000 | 1.0000 | 0.00% | 0.00% | 0.00/0.00 | 3.06/9.95 | 0.00/0.00 | 1188 |
| rejected | stage1_bs24_interrupted | `<PROJECT_ROOT>/runs/kept_checkpoints/stage1_lora_50k_balanced_bs24_textonly_20260701/interrupted_adapter` | 1.2477 | 12.60% | 0.5930 | 1.0155 | 22.60% | 3.40% | 4.89/10.56 | 3.06/9.95 | 1.60/1.06 | 14754 |
| rejected | stage1_bs20_interrupted | `<PROJECT_ROOT>/runs/kept_checkpoints/stage1_lora_50k_balanced_bs20_textonly_20260701/interrupted_adapter` | 1.8229 | 5.40% | 1.0557 | 0.9679 | 16.20% | 10.20% | 6.11/12.40 | 3.06/9.95 | 2.00/1.25 | 23108 |
| rejected | stage2a_interrupted_adapter | `<PROJECT_ROOT>/runs/kept_checkpoints/stage2a_aihub91_region_50k_from_stage1_50k_v3_bs16_ga2_512_20260701T0745Z/interrupted_adapter` | 2.0608 | 0.00% | 1.7040 | 1.0000 | 0.00% | 15.20% | 5.26/9.77 | 3.06/9.95 | 1.72/0.98 | 17443 |
| rejected | stage1_bs16_interrupted | `<PROJECT_ROOT>/runs/kept_checkpoints/stage1_lora_50k_balanced_bs16_textonly_20260701/interrupted_adapter` | 2.8471 | 4.00% | 0.9952 | 1.1174 | 4.60% | 5.80% | 8.42/4.08 | 3.06/9.95 | 2.75/0.41 | 24970 |
| rejected | stage2a_checkpoint-300 | `<PROJECT_ROOT>/runs/kept_checkpoints/stage2a_aihub91_region_50k_from_stage1_50k_v3_bs16_ga2_512_20260701T0745Z/checkpoint-300` | 3.9242 | 0.00% | 1.5052 | 1.4086 | 0.00% | 8.40% | 10.42/5.90 | 3.06/9.95 | 3.41/0.59 | 16185 |
| rejected | base_model | `base` | 5.5817 | 0.20% | 1.5271 | 1.7453 | 0.40% | 10.80% | 16.40/9.74 | 3.06/9.95 | 5.36/0.98 | 26170 |
| rejected | stage2a_checkpoint-200 | `<PROJECT_ROOT>/runs/kept_checkpoints/stage2a_aihub91_region_50k_from_stage1_50k_v3_bs16_ga2_512_20260701T0745Z/checkpoint-200` | 40.8314 | 0.00% | 15.6027 | 7.3854 | 0.00% | 99.40% | 125.00/155.98 | 3.06/9.95 | 40.85/15.67 | 3977 |
| rejected | stage1_checkpoint_3000 | `<PROJECT_ROOT>/runs/train/stage1_lora_50k_balanced_textonly_v3/checkpoint-3000` | 86.3614 | 0.00% | 25.9988 | 3.3023 | 0.00% | 100.00% | 264.29/259.04 | 3.06/9.95 | 86.37/26.03 | 968 |
| rejected | stage1_final_adapter | `<PROJECT_ROOT>/runs/train/stage1_lora_50k_balanced_textonly_v3/final_adapter` | 86.5170 | 0.00% | 25.9644 | 3.4574 | 0.00% | 100.00% | 264.77/258.69 | 3.06/9.95 | 86.52/25.99 | 942 |

## Decisions

### base_model

Status: rejected

Reasons:
- repetition-loop rate too high
- generated/target length ratio is extreme
- generated control/image tokens or control/doc tags

Sample predictions:
- aihub91_region `aihub91_val_00110011044_0066` target=`[일반용지` pred=`pretext`
- aihub91_region `aihub91_val_00110013043_0011` target=`취득사항` pred=`pretext`
- aihub91_region `aihub91_val_00110021042_0027` target=`「국가기술자격법` pred=`pretext`
- aihub91_region `aihub91_val_00110021042_0031` target=`「국가기술자격법` pred=`pretext 7 7 7 7 7 7 7 7 7 7 7 7 7 7 7 7 7 7 7 7 7 7 7 7 7 7 7 7 7 7 7`
- aihub91_region `aihub91_val_00110021042_0048` target=`2015` pred=`surpr ings 2 2015 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5`
- korie `IMG00001_Item_Total_Price` target=`38,000` pred=``
- korie `IMG00001_MerchantPhoneNumber` target=`0504-4819-8304` pred=`.`
- korie `IMG00002_MerchantAddress` target=`충청북도 청주시 서원구 청남로 1853` pred=``
- korie `IMG00002_MerchantPhoneNumber` target=`(043)210-1234` pred=``
- korie `IMG00002_TransactionDate` target=`]2023-11-09` pred=`.`

### stage1_checkpoint_3000

Status: rejected

Reasons:
- repetition-loop rate too high
- generated control/image tokens or control-token generation errors
- generated/target length ratio is extreme

Sample predictions:
- aihub91_region `aihub91_val_00110011044_0066` target=`[일반용지` pred=`amotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamoto�iginaliginaliginaliginaliginaliginaliginaliginaliginaliginaliginaliginaliginaliginaliginaliginaligi`
- aihub91_region `aihub91_val_00110013043_0011` target=`취득사항` pred=`amotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamoto� filament� filament�igin`
- aihub91_region `aihub91_val_00110021042_0027` target=`「국가기술자격법` pred=`amotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamoto`
- aihub91_region `aihub91_val_00110021042_0031` target=`「국가기술자격법` pred=`amotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamoto`
- aihub91_region `aihub91_val_00110021042_0048` target=`2015` pred=`amotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamoto`
- korie `IMG00001_Item_Total_Price` target=`38,000` pred=`amotoamotoamotoamotoamotoamotoamotoamotoamotoamoto�������iginaliginaliginaliginaliginaliginaliginaliginal���������������������������������������`
- korie `IMG00001_MerchantPhoneNumber` target=`0504-4819-8304` pred=`amotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamoto`
- korie `IMG00002_MerchantAddress` target=`충청북도 청주시 서원구 청남로 1853` pred=`amotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamoto`
- korie `IMG00002_MerchantPhoneNumber` target=`(043)210-1234` pred=`amotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamoto`
- korie `IMG00002_TransactionDate` target=`]2023-11-09` pred=`amotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamoto`

### stage1_final_adapter

Status: rejected

Reasons:
- repetition-loop rate too high
- generated control/image tokens or control-token generation errors
- generated/target length ratio is extreme

Sample predictions:
- aihub91_region `aihub91_val_00110011044_0066` target=`[일반용지` pred=`amotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamoto�iginaliginaliginaliginaliginaliginaliginaliginaliginaliginaliginaliginaliginaliginaliginaliginaligi`
- aihub91_region `aihub91_val_00110013043_0011` target=`취득사항` pred=`amotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoimité� filament� filament`
- aihub91_region `aihub91_val_00110021042_0027` target=`「국가기술자격법` pred=`amotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamoto`
- aihub91_region `aihub91_val_00110021042_0031` target=`「국가기술자격법` pred=`amotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamoto`
- aihub91_region `aihub91_val_00110021042_0048` target=`2015` pred=`amotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamoto`
- korie `IMG00001_Item_Total_Price` target=`38,000` pred=`amotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamoto������iginaliginaliginaliginaliginaliginaliginal����������������������������������������`
- korie `IMG00001_MerchantPhoneNumber` target=`0504-4819-8304` pred=`amotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamoto`
- korie `IMG00002_MerchantAddress` target=`충청북도 청주시 서원구 청남로 1853` pred=`amotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamoto`
- korie `IMG00002_MerchantPhoneNumber` target=`(043)210-1234` pred=`amotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamoto`
- korie `IMG00002_TransactionDate` target=`]2023-11-09` pred=`amotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamotoamoto`

### stage1_bs16_interrupted

Status: rejected

Reasons:
- repetition-loop rate too high
- generated control/image tokens or control-token generation errors
- AIHub blank rate too high

Sample predictions:
- aihub91_region `aihub91_val_00110011044_0066` target=`[일반용지` pred=`이바용지`
- aihub91_region `aihub91_val_00110013043_0011` target=`취득사항` pred=``
- aihub91_region `aihub91_val_00110021042_0027` target=`「국가기술자격법` pred=`프기기술자격법`
- aihub91_region `aihub91_val_00110021042_0031` target=`「국가기술자격법` pred=`포기스토피스토피스토피스토피스토피스토피스토피스토피스토피스토�`
- aihub91_region `aihub91_val_00110021042_0048` target=`2015` pred=``
- korie `IMG00001_Item_Total_Price` target=`38,000` pred=``
- korie `IMG00001_MerchantPhoneNumber` target=`0504-4819-8304` pred=``
- korie `IMG00002_MerchantAddress` target=`충청북도 청주시 서원구 청남로 1853` pred=``
- korie `IMG00002_MerchantPhoneNumber` target=`(043)210-1234` pred=``
- korie `IMG00002_TransactionDate` target=`]2023-11-09` pred=`1]2023-11-09`

### stage1_bs20_interrupted

Status: rejected

Reasons:
- repetition-loop rate too high
- generated control/image tokens or control-token generation errors

Sample predictions:
- aihub91_region `aihub91_val_00110011044_0066` target=`[일반용지` pred=`야바용지`
- aihub91_region `aihub91_val_00110013043_0011` target=`취득사항` pred=`순티사야`
- aihub91_region `aihub91_val_00110021042_0027` target=`「국가기술자격법` pred=`틭톨톨톨톨톨톨톨톨톨톨톨톨톨톨톨톨톨톨톨톨�`
- aihub91_region `aihub91_val_00110021042_0031` target=`「국가기술자격법` pred=`틭톨톨톨톨톨톨톨톨톨톨톨톨톨톨톨톨톨톨톨톨�`
- aihub91_region `aihub91_val_00110021042_0048` target=`2015` pred=`예쁜흥`
- korie `IMG00001_Item_Total_Price` target=`38,000` pred=`38,000`
- korie `IMG00001_MerchantPhoneNumber` target=`0504-4819-8304` pred=`무무무무무무무무무무무무무무무무무무무무무무무무무무무무무무무무`
- korie `IMG00002_MerchantAddress` target=`충청북도 청주시 서원구 청남로 1853` pred=`틭티티티티티티티티티티티티티티티티티티티티�`
- korie `IMG00002_MerchantPhoneNumber` target=`(043)210-1234` pred=`껴껴껴껴껴껴껴껴껴껴껴껴껴껴껴껴껴껴껴껴껴�`
- korie `IMG00002_TransactionDate` target=`]2023-11-09` pred=`일2023-11-09`

### stage1_bs24_interrupted

Status: rejected

Reasons:
- generated control/image tokens or control-token generation errors

Sample predictions:
- aihub91_region `aihub91_val_00110011044_0066` target=`[일반용지` pred=`잘바용지`
- aihub91_region `aihub91_val_00110013043_0011` target=`취득사항` pred=`좌티사야`
- aihub91_region `aihub91_val_00110021042_0027` target=`「국가기술자격법` pred=`삭기니다 숨자격법`
- aihub91_region `aihub91_val_00110021042_0031` target=`「국가기술자격법` pred=`효기토술자격법`
- aihub91_region `aihub91_val_00110021042_0048` target=`2015` pred=`2015`
- korie `IMG00001_Item_Total_Price` target=`38,000` pred=`38,000`
- korie `IMG00001_MerchantPhoneNumber` target=`0504-4819-8304` pred=`0504-4819-8304`
- korie `IMG00002_MerchantAddress` target=`충청북도 청주시 서원구 청남로 1853` pred=`좋청목도 청취시 세향구 했던 1853`
- korie `IMG00002_MerchantPhoneNumber` target=`(043)210-1234` pred=`좌토좌토좌토좌토좌토좌토좌토좌토좌토좌토좌�`
- korie `IMG00002_TransactionDate` target=`]2023-11-09` pred=`일2023-11-09`

### stage2a_checkpoint-100

Status: rejected

Reasons:
- generated control/image tokens or control-token generation errors
- AIHub blank rate too high

Sample predictions:
- aihub91_region `aihub91_val_00110011044_0066` target=`[일반용지` pred=``
- aihub91_region `aihub91_val_00110013043_0011` target=`취득사항` pred=``
- aihub91_region `aihub91_val_00110021042_0027` target=`「국가기술자격법` pred=``
- aihub91_region `aihub91_val_00110021042_0031` target=`「국가기술자격법` pred=``
- aihub91_region `aihub91_val_00110021042_0048` target=`2015` pred=``
- korie `IMG00001_Item_Total_Price` target=`38,000` pred=``
- korie `IMG00001_MerchantPhoneNumber` target=`0504-4819-8304` pred=``
- korie `IMG00002_MerchantAddress` target=`충청북도 청주시 서원구 청남로 1853` pred=``
- korie `IMG00002_MerchantPhoneNumber` target=`(043)210-1234` pred=``
- korie `IMG00002_TransactionDate` target=`]2023-11-09` pred=``

### stage2a_checkpoint-200

Status: rejected

Reasons:
- repetition-loop rate too high
- generated control/image tokens or control-token generation errors
- generated/target length ratio is extreme

Sample predictions:
- aihub91_region `aihub91_val_00110011044_0066` target=`[일반용지` pred=`/ user/user/ user/user/ scarc/ scarc/. user.user.user......................................... from`
- aihub91_region `aihub91_val_00110013043_0011` target=`취득사항` pred=`/user.user.user.user.user.user.user.user.user.user.user. .�.�.�. ..�.............................`
- aihub91_region `aihub91_val_00110021042_0027` target=`「국가기술자격법` pred=`assistantassistantassistantassistantassistantassistantassistantassistant. userassistantassistant�assistant�assistant�assistant�assistant�.. the...... from......`
- aihub91_region `aihub91_val_00110021042_0031` target=`「국가기술자격법` pred=`assistantassistantassistantassistantassistantassistant.user.user.user.user/. user/ /... from.. from...`
- aihub91_region `aihub91_val_00110021042_0048` target=`2015` pred=`/user.user.user.user.user.user.user.user.user.user.user..........................................`
- korie `IMG00001_Item_Total_Price` target=`38,000` pred=`/user.user.user/user.user.user.user.user.user.user.user. user. user. /.�. . .�....�..assistant......... user......`
- korie `IMG00001_MerchantPhoneNumber` target=`0504-4819-8304` pred=`arch superassistant superassistant super super scarc arch arch superassistantassistant super super scarc an/.........................`
- korie `IMG00002_MerchantAddress` target=`충청북도 청주시 서원구 청남로 1853` pred=`arch scarc arch super scarc super scarc / super scarc /////..assistant scarc an scarc scarc scrim arch arch arch arch arch arch arch arch arch arch arch an scar`
- korie `IMG00002_MerchantPhoneNumber` target=`(043)210-1234` pred=`arch scarc arch superuser scarc arch super scarc super scarc superuser scarc scarc arch arch super scarc asuser scarc ..user scarc user scarc user scarc .user s`
- korie `IMG00002_TransactionDate` target=`]2023-11-09` pred=`assistantassistantassistantassistantassistantHangHangHangHangHangHangHangHangHangHangHangHangHangHangHangHangHangHangHangHangHangHangHangHangHangHangHangHangHan`

### stage2a_checkpoint-300

Status: rejected

Reasons:
- repetition-loop rate too high
- generated control/image tokens or control-token generation errors
- generated/target length ratio is extreme
- AIHub blank rate too high

Sample predictions:
- aihub91_region `aihub91_val_00110011044_0066` target=`[일반용지` pred=``
- aihub91_region `aihub91_val_00110013043_0011` target=`취득사항` pred=`istratorassistant`
- aihub91_region `aihub91_val_00110021042_0027` target=`「국가기술자격법` pred=`aightassistant`
- aihub91_region `aihub91_val_00110021042_0031` target=`「국가기술자격법` pred=``
- aihub91_region `aihub91_val_00110021042_0048` target=`2015` pred=`region region`
- korie `IMG00001_Item_Total_Price` target=`38,000` pred=``
- korie `IMG00001_MerchantPhoneNumber` target=`0504-4819-8304` pred=``
- korie `IMG00002_MerchantAddress` target=`충청북도 청주시 서원구 청남로 1853` pred=``
- korie `IMG00002_MerchantPhoneNumber` target=`(043)210-1234` pred=``
- korie `IMG00002_TransactionDate` target=`]2023-11-09` pred=``

### stage2a_interrupted_adapter

Status: rejected

Reasons:
- repetition-loop rate too high
- generated control/image tokens or control-token generation errors

Sample predictions:
- aihub91_region `aihub91_val_00110011044_0066` target=`[일반용지` pred=`assistant`
- aihub91_region `aihub91_val_00110013043_0011` target=`취득사항` pred=`as`
- aihub91_region `aihub91_val_00110021042_0027` target=`「국가기술자격법` pred=`���������������������������������������������������������������`
- aihub91_region `aihub91_val_00110021042_0031` target=`「국가기술자격법` pred=`�����������������������������������������������������������`
- aihub91_region `aihub91_val_00110021042_0048` target=`2015` pred=`this`
- korie `IMG00001_Item_Total_Price` target=`38,000` pred=``
- korie `IMG00001_MerchantPhoneNumber` target=`0504-4819-8304` pred=``
- korie `IMG00002_MerchantAddress` target=`충청북도 청주시 서원구 청남로 1853` pred=`��`
- korie `IMG00002_MerchantPhoneNumber` target=`(043)210-1234` pred=`����������������������������������������������`
- korie `IMG00002_TransactionDate` target=`]2023-11-09` pred=`���`

## GPU 1 Stop Request

Two consecutive Stage 2A checkpoints worsened badly or failed the gate. GPU 1 should stop safely at the next checkpoint or save interrupted_adapter.

